"""AKTE - Unterlagen-App fuer Baufinanzierungsberater und ihre Kunden.

Starten: uvicorn main:app --port 8410
Endpunkte /gesund und /version wie bei den anderen Diensten auf reika.live.
"""
from __future__ import annotations

import hashlib
import io
import json
import secrets
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import auth
import einstellungen as E
import katalog
import ki
import pdfs
import post
import push
import scanner
from db import (Berater, Kunde, Vorgang, Beteiligter, Unterlage, Vollmacht, Ereignis, Muster, STATUS,
                jetzt, logbuch, neuer_anmeldelink, select, sitzung, verbinden)
from melden import kunde_melden, berater_melden

BASIS = Path(__file__).resolve().parent
app = FastAPI(title="AKTE", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASIS / "static"), name="static")
vorlagen = Jinja2Templates(directory=BASIS / "templates")
vorlagen.env.globals.update(STATUS=STATUS, katalog=katalog, E=E, ROLLEN=katalog.ROLLEN)
vorlagen.env.filters["fromjson"] = lambda s: (json.loads(s) if s else {})


def _abdruck() -> str:
    """Fingerabdruck des laufenden Codes fuer /version (wie bei MILLER & Co.)."""
    h = hashlib.sha256()
    for p in sorted(BASIS.glob("*.py")) + sorted((BASIS / "templates").glob("*.html")):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


ABDRUCK = _abdruck()
START = jetzt()


# --------------------------------------------------------------- Hilfen

class Umleitung(Exception):
    def __init__(self, ziel: str):
        self.ziel = ziel


@app.exception_handler(Umleitung)
async def _umleiten(_, ex: Umleitung):
    return RedirectResponse(ex.ziel, status_code=303)


def db():
    s = sitzung()
    try:
        yield s
    finally:
        s.close()


def _sitzung(request: Request):
    return auth.sitzung_lesen(request.cookies.get(auth.COOKIE))


def kunde_noetig(request: Request, s=Depends(db)) -> Kunde:
    sz = _sitzung(request)
    if not sz or sz[0] != "kunde":
        raise Umleitung("/app/anmelden")
    k = s.get(Kunde, sz[1])
    if k is None:
        raise Umleitung("/app/anmelden")
    return k


def berater_noetig(request: Request, s=Depends(db)) -> Berater:
    sz = _sitzung(request)
    if not sz or sz[0] != "berater":
        raise Umleitung("/berater/anmelden")
    b = s.get(Berater, sz[1])
    if b is None or not b.aktiv:
        raise Umleitung("/berater/anmelden")
    return b


def seite(request: Request, name: str, **ctx) -> HTMLResponse:
    ctx.setdefault("request", request)
    ctx.setdefault("heute", date.today())
    ctx.setdefault("push_oeffentlich", E.VAPID_OEFFENTLICH)
    return vorlagen.TemplateResponse(request, name, ctx)


def _sicher(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


def vorgang_aktuell(s, kunde: Kunde) -> Vorgang | None:
    """Der juengste nicht abgeschlossene Vorgang des Kunden."""
    return s.scalars(select(Vorgang).where(Vorgang.kunde_id == kunde.id,
                                           Vorgang.status.in_(("beratung", "sammeln", "freigegeben", "exportiert")))
                     .order_by(Vorgang.erstellt_am.desc())).first()


def vorgang_des_beraters(s, berater: Berater, vid: int) -> Vorgang:
    v = s.get(Vorgang, vid)
    if v is None or (v.berater_id != berater.id and v.berater.vertreter_id != berater.id):
        raise HTTPException(404)
    return v


def ordner(v: Vorgang) -> Path:
    p = E.DATEN / "vorgang" / str(v.id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _datei_speichern(v: Vorgang, name: str, daten: bytes) -> str:
    pfad = ordner(v) / name
    pfad.write_bytes(daten)
    return str(pfad)


async def _lesen(datei: UploadFile) -> bytes:
    daten = await datei.read()
    if len(daten) > E.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Datei groesser als {E.MAX_UPLOAD_MB} MB")
    return daten


def _ist_pdf(daten: bytes) -> bool:
    return daten[:5] == b"%PDF-"


def _ist_bild(daten: bytes) -> bool:
    return daten[:3] == b"\xff\xd8\xff" or daten[:8] == b"\x89PNG\r\n\x1a\n" or daten[:4] in (b"RIFF",) or daten[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1")


def einstiegsmail_senden(s, kunde: Kunde, berater: Berater) -> None:
    link = f"{E.BASIS_URL}/k/{neuer_anmeldelink(kunde)}"
    betreff, text = post.text_einstieg(kunde, berater, link)
    post.senden(s, kunde.email, betreff, text)
    logbuch(s, "einstiegsmail", f"an {kunde.email}", kunde_id=kunde.id, berater_id=berater.id)


def kunde_anlegen(s, berater: Berater, vorname: str, nachname: str, email: str, telefon: str,
                  adresse: str, herkunft: str, ausloeser: str = "berater") -> tuple[Kunde, Vorgang]:
    k = Kunde(berater_id=berater.id, vorname=vorname.strip(), nachname=nachname.strip(), email=email.strip().lower(),
              telefon=telefon.strip(), adresse=adresse.strip(), herkunft=herkunft)
    s.add(k)
    s.flush()
    v = Vorgang(kunde_id=k.id, berater_id=berater.id)
    s.add(v)
    s.flush()
    logbuch(s, "kunde_angelegt", f"{k.name} ({herkunft})", vorgang_id=v.id, kunde_id=k.id,
            berater_id=berater.id, ausloeser=ausloeser)
    einstiegsmail_senden(s, k, berater)
    return k, v


# --------------------------------------------------------------- Start

@app.on_event("startup")
def _start():
    verbinden()
    with sitzung() as s:
        if s.scalar(select(Berater).limit(1)) is None and E.BERATER_PASSWORT:
            s.add(Berater(name=E.BERATER_NAME, email=E.BERATER_EMAIL or "berater@localhost",
                          passwort_hash=auth.passwort_hash(E.BERATER_PASSWORT)))
            s.commit()


@app.get("/gesund")
def gesund():
    return {"ok": True, "seit": START.isoformat(), "ki": E.KI_AKTIV, "push": push.verfuegbar()}


@app.get("/version")
def version():
    return {"name": "AKTE", "version": E.VERSION, "abdruck": ABDRUCK}


@app.get("/", response_class=HTMLResponse)
def start(request: Request):
    sz = _sitzung(request)
    if sz and sz[0] == "berater":
        return RedirectResponse("/berater", 303)
    if sz and sz[0] == "kunde":
        return RedirectResponse("/app", 303)
    return seite(request, "start.html")


@app.get("/sw.js")
def service_worker():
    return FileResponse(BASIS / "static" / "sw.js", media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-store"})


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(BASIS / "static" / "manifest.webmanifest", media_type="application/manifest+json")


# ========================================================== Homepage-Buchung

@app.post("/api/buchung")
def buchung(request: Request, s=Depends(db), vorname: str = Form(""), nachname: str = Form(""),
            name: str = Form(""), email: str = Form(...), telefon: str = Form(""),
            berater_email: str = Form(""), schluessel: str = Form("")):
    """Wird von der Homepage nach einer Terminbuchung gerufen. Legt Kunde + Vorgang an und schickt die Einstiegsmail."""
    if not E.BUCHUNG_SCHLUESSEL or not secrets.compare_digest(schluessel, E.BUCHUNG_SCHLUESSEL):
        raise HTTPException(403)
    if name and not (vorname or nachname):
        teile = name.strip().split(" ", 1)
        vorname, nachname = teile[0], (teile[1] if len(teile) > 1 else "")
    b = None
    if berater_email:
        b = s.scalar(select(Berater).where(Berater.email == berater_email.lower(), Berater.aktiv == True))  # noqa: E712
    b = b or s.scalar(select(Berater).where(Berater.aktiv == True).order_by(Berater.id))  # noqa: E712
    if b is None:
        raise HTTPException(503, "kein Berater angelegt")
    k, v = kunde_anlegen(s, b, vorname, nachname, email, telefon, "", "homepage", ausloeser="system")
    s.commit()
    return {"ok": True, "kunde_id": k.id, "vorgang_id": v.id}


# ================================================================= KUNDE

@app.get("/k/{token}")
def anmeldelink(token: str, request: Request, s=Depends(db)):
    k = s.scalar(select(Kunde).where(Kunde.anmeldelink == token))
    if k is None or not k.anmeldelink_bis or k.anmeldelink_bis < jetzt():
        return seite(request, "kunde_anmelden.html", fehler="Dieser Link ist abgelaufen. Fordere unten einen neuen an.")
    k.letzter_login = jetzt()
    logbuch(s, "login_kunde", "per Anmeldelink", kunde_id=k.id, ausloeser="kunde")
    s.commit()
    ziel = "/app" if k.onboarding_am else "/app/start"
    antwort = RedirectResponse(ziel, 303)
    auth.cookie_setzen(antwort, "kunde", k.id, _sicher(request))
    return antwort


@app.get("/app/anmelden", response_class=HTMLResponse)
def kunde_anmelden_form(request: Request):
    return seite(request, "kunde_anmelden.html")


@app.post("/app/anmelden", response_class=HTMLResponse)
def kunde_anmelden(request: Request, s=Depends(db), email: str = Form(...)):
    k = s.scalar(select(Kunde).where(Kunde.email == email.strip().lower()).order_by(Kunde.id.desc()))
    if k:
        link = f"{E.BASIS_URL}/k/{neuer_anmeldelink(k)}"
        betreff, text = post.text_anmeldelink(k, link)
        post.senden(s, k.email, betreff, text)
        logbuch(s, "anmeldelink_angefordert", "", kunde_id=k.id, ausloeser="kunde")
        s.commit()
    return seite(request, "kunde_anmelden.html", gesendet=True)


@app.get("/app/abmelden")
def kunde_abmelden():
    antwort = RedirectResponse("/app/anmelden", 303)
    auth.cookie_loeschen(antwort)
    return antwort


@app.get("/app/start", response_class=HTMLResponse)
def onboarding_form(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    return seite(request, "kunde_start.html", kunde=k, berater=s.get(Berater, k.berater_id))


@app.post("/app/start")
def onboarding(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db),
               beschaeftigung: str = Form(...), netto_1: float = Form(...), netto_2: float = Form(...), netto_3: float = Form(...)):
    k.beschaeftigung = "selbstaendig" if beschaeftigung == "selbstaendig" else "angestellt"
    k.netto_1, k.netto_2, k.netto_3 = netto_1, netto_2, netto_3
    k.onboarding_am = jetzt()
    logbuch(s, "onboarding", f"{k.beschaeftigung}, Schnitt {(netto_1 + netto_2 + netto_3) / 3:.0f} EUR", kunde_id=k.id, ausloeser="kunde")
    b = s.get(Berater, k.berater_id)
    berater_melden(s, b, "Kunde hat Gehaelter eingetragen",
                   f"{k.name} ({k.beschaeftigung}): {netto_1:.0f} / {netto_2:.0f} / {netto_3:.0f} EUR netto.", "/berater")
    s.commit()
    return RedirectResponse("/app", 303)


def _app_kontext(s, k: Kunde) -> dict:
    v = vorgang_aktuell(s, k)
    b = s.get(Berater, k.berater_id)
    ctx = {"kunde": k, "vorgang": v, "berater": b, "push_aktiv": push.hat_abo(s, "kunde", k.id)}
    if v:
        ctx["unterlagen"] = v.unterlagen_erforderlich()
        ctx["offene_rollen"] = fehlende_rollen(v)
        ctx["beauftragbar"] = [u for u in v.unterlagen if u.status in ("fehlt", "selbst", "angefragt", "abgelehnt")
                               and katalog.typ(u.katalog_typ).beauftragbar]
        ctx["nachfragen"] = [u for u in v.unterlagen if u.status == "angefragt" and u.nachfrage_gesendet_am]
        ctx["zuletzt"] = s.scalars(select(Ereignis).where(Ereignis.vorgang_id == v.id)
                                   .order_by(Ereignis.zeit.desc()).limit(8)).all()
    return ctx


def fehlende_rollen(v: Vorgang) -> list[str]:
    """Rollen, die fuer offene Unterlagen gebraucht werden, aber nicht erfasst sind."""
    vorhanden = {b.rolle for b in v.beteiligte if b.name or b.email}
    noetig = set()
    for u in v.unterlagen_erforderlich():
        if u.status in ("akzeptiert", "beauftragt", "hochgeladen", "wartet_freigabe"):
            continue
        r = katalog.rolle_fuer_typ(katalog.typ(u.katalog_typ))
        if r:
            noetig.add(r)
    erlaubt = set(katalog.rollen_fuer_vorgang(v.modernisierung, v.modernisierung_betrag))
    return [r for r in ["makler", "verkaeufer", "notar", "architekt", "handwerker"] if r in noetig and r in erlaubt and r not in vorhanden]


@app.get("/app", response_class=HTMLResponse)
def app_home(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    if not k.onboarding_am:
        return RedirectResponse("/app/start", 303)
    ctx = _app_kontext(s, k)
    v = ctx["vorgang"]
    if v and v.status == "sammeln" and not v.beteiligte_erfasst_am:
        return RedirectResponse("/app/beteiligte", 303)
    return seite(request, "kunde_home.html", **ctx)


@app.post("/app/installiert")
def app_installiert(k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    if not k.app_installiert_am:
        k.app_installiert_am = jetzt()
        logbuch(s, "app_installiert", "", kunde_id=k.id, ausloeser="kunde")
        s.commit()
    return {"ok": True}


@app.post("/app/push")
async def app_push(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    abo = await request.json()
    push.abo_speichern(s, "kunde", k.id, abo)
    logbuch(s, "push_abo", "Kunde", kunde_id=k.id, ausloeser="kunde")
    s.commit()
    return {"ok": True}


# ---- Beteiligte

@app.get("/app/beteiligte", response_class=HTMLResponse)
def beteiligte_form(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    v = vorgang_aktuell(s, k)
    if v is None:
        return RedirectResponse("/app", 303)
    rollen = katalog.rollen_fuer_vorgang(v.modernisierung, v.modernisierung_betrag)
    vorhanden = {b.rolle: b for b in v.beteiligte if b.rolle != "handwerker"}
    handwerker = [b for b in v.beteiligte if b.rolle == "handwerker"]
    return seite(request, "kunde_beteiligte.html", kunde=k, vorgang=v, rollen=rollen, vorhanden=vorhanden,
                 handwerker=handwerker, berater=s.get(Berater, k.berater_id))


@app.post("/app/beteiligte")
async def beteiligte_speichern(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    v = vorgang_aktuell(s, k)
    if v is None:
        return RedirectResponse("/app", 303)
    form = await request.form()
    for b in list(v.beteiligte):
        s.delete(b)
    s.flush()
    for rolle in ("makler", "verkaeufer", "notar", "architekt"):
        name, email = form.get(f"{rolle}_name", "").strip(), form.get(f"{rolle}_email", "").strip()
        adresse = form.get(f"{rolle}_adresse", "").strip()
        if name or email or adresse:
            s.add(Beteiligter(vorgang_id=v.id, rolle=rolle, name=name, email=email, adresse=adresse))
    for i in range(1, 6):
        name = form.get(f"handwerker_{i}_name", "").strip()
        if name:
            s.add(Beteiligter(vorgang_id=v.id, rolle="handwerker", name=name,
                              adresse=form.get(f"handwerker_{i}_adresse", "").strip(),
                              gewerk=form.get(f"handwerker_{i}_gewerk", "").strip(),
                              email=form.get(f"handwerker_{i}_email", "").strip()))
    v.beteiligte_erfasst_am = jetzt()
    logbuch(s, "beteiligte_erfasst", "", vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
    s.commit()
    s.refresh(v)
    if fehlende_rollen(v):
        return RedirectResponse("/app/beschaffung?warnung=1", 303)
    return RedirectResponse("/app", 303)


# ---- Beschaffungsauftrag

@app.get("/app/beschaffung", response_class=HTMLResponse)
def beschaffung_form(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db), warnung: int = 0):
    ctx = _app_kontext(s, k)
    if ctx["vorgang"] is None:
        return RedirectResponse("/app", 303)
    b = ctx["berater"]
    for u in ctx["beauftragbar"]:
        if u.preis_beschaffung is None:
            u.preis_beschaffung = b.preis_beschaffung
    return seite(request, "kunde_beschaffung.html", warnung=bool(warnung), **ctx)


@app.post("/app/beschaffung")
async def beschaffung_erteilen(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    v = vorgang_aktuell(s, k)
    if v is None:
        return RedirectResponse("/app", 303)
    form = await request.form()
    ids = [int(x) for x in form.getlist("unterlage")]
    unterschrift = form.get("unterschrift", "")
    if not ids or not unterschrift.startswith("data:image/png;base64,"):
        return RedirectResponse("/app/beschaffung?fehler=1", 303)
    import base64
    png = base64.b64decode(unterschrift.split(",", 1)[1])
    b = s.get(Berater, k.berater_id)
    gewaehlt = [u for u in v.unterlagen if u.id in ids and katalog.typ(u.katalog_typ).beauftragbar]
    for u in gewaehlt:
        if u.preis_beschaffung is None:
            u.preis_beschaffung = b.preis_beschaffung
    betrag = sum(u.preis_beschaffung or 0 for u in gewaehlt)
    pdf = pdfs.auftrag_und_vollmacht(v, k, b, gewaehlt, betrag, png)
    pfad = _datei_speichern(v, f"auftrag_{jetzt().strftime('%Y%m%d%H%M%S')}.pdf", pdf)
    s.add(Vollmacht(vorgang_id=v.id, art="auftrag", datei=pfad, unterlagen_ids=json.dumps(ids), betrag=betrag))
    for u in gewaehlt:
        u.status = "beauftragt"
    v.vollmacht_berater_am = jetzt()
    v.vollmacht_berater_datei = pfad
    v.hilfe_abgelehnt_am = None
    logbuch(s, "beschaffungsauftrag", f"{len(gewaehlt)} Unterlagen, {betrag:.2f} EUR, in der App unterschrieben",
            vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
    berater_melden(s, b, "Beschaffungsauftrag erteilt",
                   f"{k.name} hat dich mit {len(gewaehlt)} Unterlage(n) beauftragt ({betrag:.2f} EUR) und die Vollmacht unterschrieben.",
                   f"/berater/vorgang/{v.id}", vorgang_id=v.id)
    s.commit()
    return RedirectResponse("/app?auftrag=1", 303)


@app.post("/app/beschaffung/ablehnen")
def beschaffung_ablehnen(k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    v = vorgang_aktuell(s, k)
    if v:
        v.hilfe_abgelehnt_am = jetzt()
        v.hilfe_erinnert_am = date.today()
        logbuch(s, "hilfe_abgelehnt", "Kunde besorgt alles selbst; Haftungshinweis angezeigt",
                vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
        s.commit()
    return RedirectResponse("/app?abgelehnt=1", 303)


@app.get("/app/vorlage/vollmacht-verkaeufer.pdf")
def vorlage_verkaeufer(k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    v = vorgang_aktuell(s, k)
    if v is None:
        raise HTTPException(404)
    verk = next((b for b in v.beteiligte if b.rolle == "verkaeufer"), None)
    typen = [u.katalog_typ for u in v.unterlagen_erforderlich() if katalog.typ(u.katalog_typ).vollmacht == katalog.VM_VERKAEUFER]
    pdf = pdfs.vollmacht_verkaeufer(v, k, s.get(Berater, k.berater_id), verk, typen)
    logbuch(s, "vorlage_verkaeufer", "heruntergeladen", vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
    s.commit()
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=vollmacht-verkaeufer.pdf"})


# ---- Unterlage

def _unterlage_des_kunden(s, k: Kunde, uid: int) -> tuple[Vorgang, Unterlage]:
    v = vorgang_aktuell(s, k)
    u = s.get(Unterlage, uid)
    if v is None or u is None or u.vorgang_id != v.id:
        raise HTTPException(404)
    return v, u


@app.get("/app/unterlage/{uid}", response_class=HTMLResponse)
def unterlage_seite(uid: int, request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    v, u = _unterlage_des_kunden(s, k, uid)
    typ = katalog.typ(u.katalog_typ)
    makler = next((b for b in v.beteiligte if b.rolle == "makler"), None)
    mailto = ""
    if typ.quelle in (katalog.MAKLER, katalog.VERKAEUFER_VOLLMACHT, katalog.DIENSTLEISTER) and makler and makler.email:
        offene = [x for x in v.unterlagen_erforderlich() if x.status in ("fehlt", "abgelehnt") and
                  katalog.typ(x.katalog_typ).quelle in (katalog.MAKLER, katalog.VERKAEUFER_VOLLMACHT, katalog.DIENSTLEISTER)]
        if u not in offene:
            offene.insert(0, u)
        betreff, text = post.makler_mail_text(k, v, offene, makler.name)
        mailto = f"mailto:{makler.email}?" + urllib.parse.urlencode({"subject": betreff, "body": text}, quote_via=urllib.parse.quote)
    muster = s.scalars(select(Muster).where(Muster.katalog_typ == u.katalog_typ)).all()
    return seite(request, "kunde_unterlage.html", kunde=k, vorgang=v, u=u, typ=typ, makler=makler, mailto=mailto,
                 muster=muster, berater=s.get(Berater, k.berater_id), push_aktiv=push.hat_abo(s, "kunde", k.id))


def unterlage_pruefen_und_ablegen(s, v: Vorgang, u: Unterlage, pdf: bytes, von: str, ausloeser: str) -> dict:
    """Gemeinsamer Weg fuer Kunden- und Berater-Upload: pruefen, ablegen, Status setzen, melden."""
    k = v.kunde
    ergebnis = ki.unterlage_pruefen(pdf, u.katalog_typ, u.bezeichnung, k.nachname)
    u.versuche += 1
    name = f"unterlage_{u.id}_{u.versuche}.pdf"
    u.datei = _datei_speichern(v, name, pdf)
    u.dateiname = ergebnis.get("dateiname") or name
    u.hochgeladen_von, u.hochgeladen_am = von, jetzt()
    u.ki_ergebnis = json.dumps(ergebnis, ensure_ascii=False)
    u.fehlerliste = json.dumps(ergebnis.get("fehler") or [], ensure_ascii=False)
    passt = ergebnis.get("passt")
    if passt is False:
        u.status = "abgelehnt"
    elif passt is None or u.kritisch or katalog.typ(u.katalog_typ).kritisch:
        u.status = "wartet_freigabe"
    else:
        u.status = "akzeptiert"
        u.geprueft_am = jetzt()
    logbuch(s, "upload", f"{u.bezeichnung}: {u.status} ({ergebnis.get('quelle')}) von {von}",
            vorgang_id=v.id, kunde_id=k.id, ausloeser=ausloeser)
    if von == "kunde":
        berater_melden(s, v.berater, "Unterlage hochgeladen",
                       f"{k.name}: {u.bezeichnung} ist {u.status_text}.", f"/berater/vorgang/{v.id}", vorgang_id=v.id)
    return ergebnis


@app.post("/app/unterlage/{uid}/upload")
async def unterlage_upload(uid: int, k: Kunde = Depends(kunde_noetig), s=Depends(db),
                           dateien: list[UploadFile] = File(...)):
    v, u = _unterlage_des_kunden(s, k, uid)
    inhalte = [await _lesen(d) for d in dateien if d.filename]
    if not inhalte:
        return RedirectResponse(f"/app/unterlage/{uid}?fehler=leer", 303)
    if len(inhalte) == 1 and _ist_pdf(inhalte[0]):
        pdf = inhalte[0]
    elif all(_ist_bild(b) for b in inhalte):
        pdf, maengel = scanner.fotos_zu_pdf(inhalte)
        if pdf is None:
            fehler = [f"Foto {i + 1}: {m}" for i, liste in enumerate(maengel) for m in liste] or ["Kein Foto konnte verarbeitet werden."]
            u.fehlerliste = json.dumps(fehler, ensure_ascii=False)
            logbuch(s, "scan_abgelehnt", "; ".join(fehler), vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
            s.commit()
            return RedirectResponse(f"/app/unterlage/{uid}?fehler=scan", 303)
        logbuch(s, "scan", f"{len(inhalte)} Foto(s) zu PDF", vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
    else:
        u.fehlerliste = json.dumps(["Bitte entweder ein PDF oder nur Fotos hochladen, nicht gemischt."], ensure_ascii=False)
        s.commit()
        return RedirectResponse(f"/app/unterlage/{uid}?fehler=format", 303)
    unterlage_pruefen_und_ablegen(s, v, u, pdf, "kunde", "kunde")
    s.commit()
    return RedirectResponse(f"/app/unterlage/{uid}?geprueft=1", 303)


@app.post("/app/unterlage/{uid}/makler-gesendet")
def makler_gesendet(uid: int, k: Kunde = Depends(kunde_noetig), s=Depends(db), mahnung: int = Form(0)):
    v, u = _unterlage_des_kunden(s, k, uid)
    # Alle offenen Makler-Positionen gelten als angefragt (die Mail listet sie alle)
    for x in v.unterlagen_erforderlich():
        q = katalog.typ(x.katalog_typ).quelle
        if x.id == u.id or (x.status in ("fehlt", "abgelehnt") and q in (katalog.MAKLER, katalog.VERKAEUFER_VOLLMACHT, katalog.DIENSTLEISTER)):
            if mahnung:
                x.mahnung_am = jetzt()
            else:
                x.makler_mail_am = jetzt()
            x.status = "angefragt"
            x.nachfrage_am = jetzt() + timedelta(days=E.NACHFRAGE_MAKLER_TAGE)
            x.nachfrage_gesendet_am = None
    logbuch(s, "makler_mahnung" if mahnung else "makler_mail", f"Kunde bestaetigt Versand ({u.bezeichnung})",
            vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
    s.commit()
    return RedirectResponse("/app", 303)


@app.post("/app/unterlage/{uid}/selbst")
def selbst_besorgen(uid: int, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    v, u = _unterlage_des_kunden(s, k, uid)
    u.status = "selbst"
    logbuch(s, "selbst_besorgen", u.bezeichnung, vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
    s.commit()
    return RedirectResponse(f"/app/unterlage/{uid}", 303)


@app.get("/app/nachfrage", response_class=HTMLResponse)
def nachfrage(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    ctx = _app_kontext(s, k)
    v = ctx["vorgang"]
    if v is None:
        return RedirectResponse("/app", 303)
    makler = next((b for b in v.beteiligte if b.rolle == "makler"), None)
    angefragt = [u for u in v.unterlagen if u.status == "angefragt"]
    mailto = ""
    if makler and makler.email and angefragt:
        betreff, text = post.makler_mail_text(k, v, angefragt, makler.name, mahnung=True)
        mailto = f"mailto:{makler.email}?" + urllib.parse.urlencode({"subject": betreff, "body": text}, quote_via=urllib.parse.quote)
    return seite(request, "kunde_nachfrage.html", angefragt=angefragt, mailto=mailto, makler=makler, **ctx)


@app.post("/app/freigabe")
def freigabe_kunde(k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    v = vorgang_aktuell(s, k)
    if v and v.alles_akzeptiert and not v.freigabe_kunde_am:
        v.freigabe_kunde_am = jetzt()
        v.status = "freigegeben"
        logbuch(s, "freigabe_kunde", "Kunde gibt Unterlagen in der App frei", vorgang_id=v.id, kunde_id=k.id, ausloeser="kunde")
        berater_melden(s, v.berater, "Unterlagen freigegeben",
                       f"{k.name} hat alle Unterlagen freigegeben. Du kannst jetzt exportieren.",
                       f"/berater/vorgang/{v.id}", vorgang_id=v.id)
        s.commit()
    return RedirectResponse("/app", 303)


@app.get("/app/muster", response_class=HTMLResponse)
def muster_liste(request: Request, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    return seite(request, "kunde_muster.html", kunde=k, muster=s.scalars(select(Muster).order_by(Muster.titel)).all())


@app.get("/app/muster/{mid}")
def muster_laden(mid: int, k: Kunde = Depends(kunde_noetig), s=Depends(db)):
    m = s.get(Muster, mid)
    if m is None:
        raise HTTPException(404)
    return FileResponse(m.datei, media_type="application/pdf", filename=Path(m.datei).name)


# ================================================================ BERATER

@app.get("/berater/anmelden", response_class=HTMLResponse)
def berater_anmelden_form(request: Request):
    return seite(request, "berater_anmelden.html")


@app.post("/berater/anmelden", response_class=HTMLResponse)
def berater_anmelden(request: Request, s=Depends(db), email: str = Form(...), passwort: str = Form(...)):
    b = s.scalar(select(Berater).where(Berater.email == email.strip().lower()))
    if b is None or not b.aktiv or not auth.passwort_pruefen(passwort, b.passwort_hash):
        logbuch(s, "login_berater_fehl", email.strip().lower()[:100])
        s.commit()
        return seite(request, "berater_anmelden.html", fehler="E-Mail oder Passwort stimmen nicht.")
    logbuch(s, "login_berater", "", berater_id=b.id, ausloeser="berater")
    s.commit()
    antwort = RedirectResponse("/berater", 303)
    auth.cookie_setzen(antwort, "berater", b.id, _sicher(request))
    return antwort


@app.get("/berater/abmelden")
def berater_abmelden():
    antwort = RedirectResponse("/berater/anmelden", 303)
    auth.cookie_loeschen(antwort)
    return antwort


@app.get("/berater", response_class=HTMLResponse)
def dashboard(request: Request, b: Berater = Depends(berater_noetig), s=Depends(db)):
    eigene = s.scalars(select(Vorgang).where(Vorgang.berater_id == b.id)).all()
    vertretung = s.scalars(select(Vorgang).join(Berater, Vorgang.berater_id == Berater.id)
                           .where(Berater.vertreter_id == b.id)).all()
    alle = [v for v in eigene + vertretung if v.status not in ("abgeschlossen", "abgebrochen")]

    def sortierung(v: Vorgang):
        r = v.zins_tage_rest
        return (0 if r is not None and r < 0 else 1 if r is not None else 2, r if r is not None else 9999)
    alle.sort(key=sortierung)
    zeilen = []
    for v in alle:
        zeilen.append({
            "v": v, "fortschritt": v.fortschritt,
            "freigaben": sum(1 for u in v.unterlagen if u.status == "wartet_freigabe"),
            "unsicher": sum(1 for u in v.unterlagen if not u.zuordnung_sicher),
            "beauftragt": sum(1 for u in v.unterlagen if u.status == "beauftragt"),
            "push": push.hat_abo(s, "kunde", v.kunde_id),
            "vertretung": v.berater_id != b.id,
        })
    return seite(request, "berater_dashboard.html", berater=b, zeilen=zeilen,
                 push_aktiv=push.hat_abo(s, "berater", b.id))


@app.post("/berater/push")
async def berater_push(request: Request, b: Berater = Depends(berater_noetig), s=Depends(db)):
    push.abo_speichern(s, "berater", b.id, await request.json())
    s.commit()
    return {"ok": True}


@app.get("/berater/kunde/neu", response_class=HTMLResponse)
def kunde_neu_form(request: Request, b: Berater = Depends(berater_noetig)):
    return seite(request, "berater_kunde_neu.html", berater=b)


@app.post("/berater/kunde/neu")
def kunde_neu(b: Berater = Depends(berater_noetig), s=Depends(db), vorname: str = Form(...), nachname: str = Form(...),
              email: str = Form(...), telefon: str = Form(""), adresse: str = Form(""), herkunft: str = Form("berater")):
    k, v = kunde_anlegen(s, b, vorname, nachname, email, telefon, adresse, herkunft, ausloeser="berater")
    s.commit()
    return RedirectResponse(f"/berater/vorgang/{v.id}?neu=1", 303)


@app.get("/berater/vorgang/{vid}", response_class=HTMLResponse)
def vorgang_seite(vid: int, request: Request, b: Berater = Depends(berater_noetig), s=Depends(db)):
    v = vorgang_des_beraters(s, b, vid)
    ereignisse = s.scalars(select(Ereignis).where(Ereignis.vorgang_id == v.id).order_by(Ereignis.zeit.desc()).limit(50)).all()
    vollmachten = s.scalars(select(Vollmacht).where(Vollmacht.vorgang_id == v.id)).all()
    return seite(request, "berater_vorgang.html", berater=b, vorgang=v, kunde=v.kunde, ereignisse=ereignisse,
                 vollmachten=vollmachten, push_kunde=push.hat_abo(s, "kunde", v.kunde_id),
                 typen=katalog.TYPEN, offene_rollen=fehlende_rollen(v))


@app.post("/berater/vorgang/{vid}/daten")
def vorgang_daten(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db), bezeichnung: str = Form(""),
                  bank: str = Form(""), zins_gueltig_bis: str = Form(""), modernisierung: str = Form(""),
                  modernisierung_betrag: str = Form("")):
    v = vorgang_des_beraters(s, b, vid)
    v.bezeichnung, v.bank = bezeichnung.strip(), bank.strip()
    alt = v.zins_gueltig_bis
    v.zins_gueltig_bis = date.fromisoformat(zins_gueltig_bis) if zins_gueltig_bis else None
    if v.zins_gueltig_bis != alt:
        v.zins_erinnert_am = None
        v.zins_wochen_erinnert_am = None
        logbuch(s, "zinsdatum", f"{alt} -> {v.zins_gueltig_bis}", vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
        if alt and v.zins_gueltig_bis and v.status == "sammeln":
            kunde_melden(s, v.kunde, "Neue Zinskondition",
                         f"Dein Berater hat ein neues Angebot eingespielt. Die Kondition gilt bis {v.zins_gueltig_bis.strftime('%d.%m.%Y')}.")
    v.modernisierung = modernisierung == "ja"
    try:
        v.modernisierung_betrag = float(modernisierung_betrag.replace(".", "").replace(",", ".")) if modernisierung_betrag else None
    except ValueError:
        v.modernisierung_betrag = None
    s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}", 303)


@app.post("/berater/vorgang/{vid}/liste")
async def liste_hochladen(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db), datei: UploadFile = File(...)):
    v = vorgang_des_beraters(s, b, vid)
    pdf = await _lesen(datei)
    if not _ist_pdf(pdf):
        raise HTTPException(400, "Bitte die Unterlagenliste als PDF hochladen.")
    v.liste_datei = _datei_speichern(v, "unterlagenliste.pdf", pdf)
    v.liste_hochgeladen_am = jetzt()
    gelesen = ki.liste_lesen(pdf)
    if gelesen.get("bank") and not v.bank:
        v.bank = gelesen["bank"]
    vorhanden = {u.katalog_typ for u in v.unterlagen}
    neu = 0
    for i, p in enumerate(gelesen["positionen"]):
        typ = katalog.typ(p["katalog_typ"])
        if typ.schluessel in vorhanden and typ.schluessel != "sonstiges":
            continue
        if typ.nur_selbstaendig and v.kunde.beschaeftigung != "selbstaendig":
            pass  # steht die Bankliste drin, bleibt es drin
        s.add(Unterlage(vorgang_id=v.id, reihenfolge=len(v.unterlagen) + i, bezeichnung=p["bezeichnung"][:300],
                        katalog_typ=typ.schluessel, zuordnung_sicher=bool(p.get("sicher")), kritisch=typ.kritisch))
        vorhanden.add(typ.schluessel)
        neu += 1
    erster = v.status == "beratung"
    v.status = "sammeln"
    logbuch(s, "liste_hochgeladen", f"{neu} Positionen ({gelesen.get('quelle')})", vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    s.commit()
    s.refresh(v)
    if neu or erster:
        kunde_melden(s, v.kunde, "Deine Unterlagenliste ist da",
                     f"Die Bank braucht {len(v.unterlagen_erforderlich())} Unterlagen. Oeffne die App und leg los.", "/app")
        s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}?liste={neu}", 303)


@app.post("/berater/vorgang/{vid}/unterlage/neu")
def unterlage_neu(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db), bezeichnung: str = Form(...), katalog_typ: str = Form("sonstiges")):
    v = vorgang_des_beraters(s, b, vid)
    typ = katalog.typ(katalog_typ)
    s.add(Unterlage(vorgang_id=v.id, reihenfolge=len(v.unterlagen), bezeichnung=bezeichnung.strip()[:300],
                    katalog_typ=typ.schluessel, kritisch=typ.kritisch))
    logbuch(s, "unterlage_ergaenzt", bezeichnung.strip(), vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    if v.status == "sammeln":
        kunde_melden(s, v.kunde, "Neue Unterlage in deiner Liste", f"Die Bank braucht zusaetzlich: {bezeichnung.strip()}", "/app")
    s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}", 303)


@app.post("/berater/vorgang/{vid}/unterlage/{uid}")
def unterlage_aktion(vid: int, uid: int, b: Berater = Depends(berater_noetig), s=Depends(db), aktion: str = Form(...),
                     kommentar: str = Form(""), katalog_typ: str = Form(""), preis: str = Form("")):
    v = vorgang_des_beraters(s, b, vid)
    u = s.get(Unterlage, uid)
    if u is None or u.vorgang_id != v.id:
        raise HTTPException(404)
    k = v.kunde
    if aktion == "freigeben":
        u.status, u.geprueft_am, u.berater_kommentar = "akzeptiert", jetzt(), kommentar.strip()
        logbuch(s, "beraterfreigabe", u.bezeichnung, vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
        kunde_melden(s, k, "Unterlage akzeptiert", f"{u.bezeichnung} ist von deinem Berater freigegeben.", f"/app/unterlage/{u.id}")
    elif aktion == "ablehnen":
        u.status, u.geprueft_am, u.berater_kommentar = "abgelehnt", jetzt(), kommentar.strip()
        fehler = u.fehler
        if kommentar.strip():
            fehler = [f"Berater: {kommentar.strip()}"] + fehler
        u.fehlerliste = json.dumps(fehler, ensure_ascii=False)
        logbuch(s, "beraterablehnung", f"{u.bezeichnung}: {kommentar.strip()}", vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
        kunde_melden(s, k, "Unterlage abgelehnt", f"{u.bezeichnung}: {kommentar.strip() or 'bitte Fehlerliste pruefen'}", f"/app/unterlage/{u.id}")
    elif aktion == "typ":
        typ = katalog.typ(katalog_typ)
        u.katalog_typ, u.zuordnung_sicher, u.kritisch = typ.schluessel, True, typ.kritisch
        logbuch(s, "zuordnung", f"{u.bezeichnung} -> {typ.schluessel}", vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    elif aktion == "bestaetigen":
        u.zuordnung_sicher = True
    elif aktion == "preis":
        try:
            u.preis_beschaffung = float(preis.replace(",", ".")) if preis.strip() else None
        except ValueError:
            pass
    elif aktion == "nicht_erforderlich":
        u.status = "nicht_erforderlich"
        logbuch(s, "nicht_erforderlich", u.bezeichnung, vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    elif aktion == "zuruecksetzen":
        u.status, u.fehlerliste, u.berater_kommentar = "fehlt", "", ""
        logbuch(s, "zurueckgesetzt", u.bezeichnung, vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    elif aktion == "erledigt":  # Berater hat die beauftragte Unterlage besorgt, ohne sie hochzuladen (z. B. direkt an die Bank)
        u.status = "akzeptiert"
        u.geprueft_am = jetzt()
        logbuch(s, "beschafft", u.bezeichnung, vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}#u{uid}", 303)


@app.post("/berater/vorgang/{vid}/unterlage/{uid}/upload")
async def berater_upload(vid: int, uid: int, b: Berater = Depends(berater_noetig), s=Depends(db), datei: UploadFile = File(...)):
    v = vorgang_des_beraters(s, b, vid)
    u = s.get(Unterlage, uid)
    if u is None or u.vorgang_id != v.id:
        raise HTTPException(404)
    if not v.vollmacht_vorhanden:
        raise HTTPException(403, "Ohne Vollmacht des Kunden darf der Berater keine Unterlagen hochladen.")
    pdf = await _lesen(datei)
    if not _ist_pdf(pdf):
        raise HTTPException(400, "Bitte als PDF hochladen.")
    unterlage_pruefen_und_ablegen(s, v, u, pdf, "berater", "berater")
    if u.status == "wartet_freigabe":
        pass  # Berater gibt direkt in der Liste frei
    kunde_melden(s, v.kunde, "Dein Berater hat eine Unterlage hochgeladen", f"{u.bezeichnung} ist jetzt {u.status_text}.", f"/app/unterlage/{u.id}")
    s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}#u{uid}", 303)


@app.post("/berater/vorgang/{vid}/vollmacht")
async def vollmacht_schriftlich(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db), datei: UploadFile = File(...)):
    """Schriftliche Vollmacht des Kunden liegt vor (ausserhalb der App unterschrieben)."""
    v = vorgang_des_beraters(s, b, vid)
    pdf = await _lesen(datei)
    if not _ist_pdf(pdf):
        raise HTTPException(400, "Bitte als PDF hochladen.")
    pfad = _datei_speichern(v, f"vollmacht_schriftlich_{jetzt().strftime('%Y%m%d%H%M%S')}.pdf", pdf)
    s.add(Vollmacht(vorgang_id=v.id, art="berater", datei=pfad))
    v.vollmacht_berater_am = v.vollmacht_berater_am or jetzt()
    v.vollmacht_berater_datei = v.vollmacht_berater_datei or pfad
    logbuch(s, "vollmacht_schriftlich", "vom Berater hinterlegt", vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}", 303)


@app.post("/berater/vorgang/{vid}/freigabe-schriftlich")
def freigabe_schriftlich(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db), bestaetigt: str = Form("")):
    v = vorgang_des_beraters(s, b, vid)
    v.freigabe_schriftlich = bestaetigt == "ja"
    if v.freigabe_schriftlich and v.alles_akzeptiert:
        v.status = "freigegeben"
    logbuch(s, "freigabe_schriftlich", "ja" if v.freigabe_schriftlich else "nein", vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}", 303)


@app.post("/berater/vorgang/{vid}/status")
def vorgang_status(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db), status: str = Form(...)):
    v = vorgang_des_beraters(s, b, vid)
    if status in ("beratung", "sammeln", "abgeschlossen", "abgebrochen"):
        logbuch(s, "status", f"{v.status} -> {status}", vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
        v.status = status
        s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}", 303)


@app.post("/berater/vorgang/{vid}/einstiegsmail")
def einstiegsmail_erneut(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db)):
    v = vorgang_des_beraters(s, b, vid)
    einstiegsmail_senden(s, v.kunde, b)
    s.commit()
    return RedirectResponse(f"/berater/vorgang/{vid}?mail=1", 303)


@app.get("/berater/vorgang/{vid}/datei/{uid}")
def datei_laden(vid: int, uid: int, b: Berater = Depends(berater_noetig), s=Depends(db)):
    v = vorgang_des_beraters(s, b, vid)
    u = s.get(Unterlage, uid)
    if u is None or u.vorgang_id != v.id or not u.datei:
        raise HTTPException(404)
    return FileResponse(u.datei, media_type="application/pdf", filename=u.dateiname or Path(u.datei).name)


@app.get("/berater/vorgang/{vid}/liste.pdf")
def liste_laden(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db)):
    v = vorgang_des_beraters(s, b, vid)
    if not v.liste_datei:
        raise HTTPException(404)
    return FileResponse(v.liste_datei, media_type="application/pdf", filename="unterlagenliste.pdf")


@app.get("/berater/vorgang/{vid}/vollmacht/{vmid}")
def vollmacht_laden(vid: int, vmid: int, b: Berater = Depends(berater_noetig), s=Depends(db)):
    v = vorgang_des_beraters(s, b, vid)
    vm = s.get(Vollmacht, vmid)
    if vm is None or vm.vorgang_id != v.id:
        raise HTTPException(404)
    return FileResponse(vm.datei, media_type="application/pdf", filename=Path(vm.datei).name)


@app.get("/berater/vorgang/{vid}/export.zip")
def export(vid: int, b: Berater = Depends(berater_noetig), s=Depends(db)):
    v = vorgang_des_beraters(s, b, vid)
    if not v.export_moeglich:
        raise HTTPException(409, "Export erst, wenn alle Unterlagen akzeptiert und vom Kunden freigegeben sind.")
    dateien = [(u.dateiname or Path(u.datei).name, Path(u.datei).read_bytes())
               for u in v.unterlagen_erforderlich() if u.datei and Path(u.datei).exists()]
    vollmachten = [(Path(vm.datei).name, Path(vm.datei).read_bytes())
                   for vm in s.scalars(select(Vollmacht).where(Vollmacht.vorgang_id == v.id)).all() if Path(vm.datei).exists()]
    paket = pdfs.export_paket(v, v.kunde, dateien, vollmachten)
    v.exportiert_am = jetzt()
    v.status = "exportiert"
    logbuch(s, "export", f"{len(dateien)} Dateien", vorgang_id=v.id, berater_id=b.id, ausloeser="berater")
    s.commit()
    name = f"unterlagen-{v.kunde.nachname.lower()}-{v.id}.zip"
    return Response(paket, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={name}"})


@app.get("/berater/einstellungen", response_class=HTMLResponse)
def einstellungen_form(request: Request, b: Berater = Depends(berater_noetig), s=Depends(db)):
    andere = s.scalars(select(Berater).where(Berater.id != b.id, Berater.aktiv == True)).all()  # noqa: E712
    return seite(request, "berater_einstellungen.html", berater=b, andere=andere, push_aktiv=push.hat_abo(s, "berater", b.id),
                 muster=s.scalars(select(Muster).order_by(Muster.titel)).all())


@app.post("/berater/einstellungen")
def einstellungen_speichern(b: Berater = Depends(berater_noetig), s=Depends(db), name: str = Form(...), email: str = Form(...),
                            telefon: str = Form(""), preis_beschaffung: str = Form("0"), vertreter_id: str = Form(""),
                            passwort: str = Form("")):
    b.name, b.email, b.telefon = name.strip(), email.strip().lower(), telefon.strip()
    try:
        b.preis_beschaffung = float(preis_beschaffung.replace(",", ".") or 0)
    except ValueError:
        pass
    b.vertreter_id = int(vertreter_id) if vertreter_id.isdigit() else None
    if passwort.strip():
        b.passwort_hash = auth.passwort_hash(passwort)
        logbuch(s, "passwort_geaendert", "", berater_id=b.id, ausloeser="berater")
    s.commit()
    return RedirectResponse("/berater/einstellungen?ok=1", 303)


@app.post("/berater/berater/neu")
def berater_neu(b: Berater = Depends(berater_noetig), s=Depends(db), name: str = Form(...), email: str = Form(...), passwort: str = Form(...)):
    s.add(Berater(name=name.strip(), email=email.strip().lower(), passwort_hash=auth.passwort_hash(passwort),
                  organisation_id=b.organisation_id))
    logbuch(s, "berater_angelegt", email.strip().lower(), berater_id=b.id, ausloeser="berater")
    s.commit()
    return RedirectResponse("/berater/einstellungen", 303)


@app.post("/berater/muster")
async def muster_hochladen(b: Berater = Depends(berater_noetig), s=Depends(db), titel: str = Form(...),
                           beschreibung: str = Form(""), katalog_typ: str = Form(""), datei: UploadFile = File(...)):
    pdf = await _lesen(datei)
    if not _ist_pdf(pdf):
        raise HTTPException(400, "Bitte als PDF hochladen.")
    p = E.DATEN / "muster"
    p.mkdir(parents=True, exist_ok=True)
    name = f"{jetzt().strftime('%Y%m%d%H%M%S')}-{''.join(c for c in titel if c.isalnum())[:40]}.pdf"
    (p / name).write_bytes(pdf)
    s.add(Muster(titel=titel.strip(), beschreibung=beschreibung.strip(), katalog_typ=katalog_typ, datei=str(p / name)))
    logbuch(s, "muster_hochgeladen", titel.strip(), berater_id=b.id, ausloeser="berater")
    s.commit()
    return RedirectResponse("/berater/einstellungen", 303)


@app.post("/berater/muster/{mid}/loeschen")
def muster_loeschen(mid: int, b: Berater = Depends(berater_noetig), s=Depends(db)):
    m = s.get(Muster, mid)
    if m:
        s.delete(m)
        logbuch(s, "muster_geloescht", m.titel, berater_id=b.id, ausloeser="berater")
        s.commit()
    return RedirectResponse("/berater/einstellungen", 303)
