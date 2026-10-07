"""Selbsttest-Gates fuer AKTE. Laeuft lokal und auf dem Server vor jedem Ausrollen.

Aufruf: python selftest.py            (alle Gates)
        AKTE_NUR=<gate> python selftest.py   (ein Gate)
Jedes Gate ist eine Funktion mit @gate("satz-mit-bindestrichen"). Rot = Ausroll-Abbruch.
"""
import io
import os
import sys
import tempfile
import traceback
from datetime import date, timedelta

os.environ.setdefault("AKTE_DATEN", tempfile.mkdtemp(prefix="akte-selftest-"))
os.environ["DATABASE_URL"] = f"sqlite:///{os.environ['AKTE_DATEN']}/test.db"
os.environ["AKTE_BERATER_PASSWORT"] = "test1234"
os.environ["AKTE_BERATER_EMAIL"] = "berater@example.org"
os.environ["AKTE_BUCHUNG_SCHLUESSEL"] = "buchung-geheim"
os.environ["AKTE_SMTP_HOST"] = ""
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

import db  # noqa: E402
import einstellungen as E  # noqa: E402
import katalog  # noqa: E402
import ki  # noqa: E402
import push  # noqa: E402
import scanner  # noqa: E402
import zeitplan  # noqa: E402
from db import Kunde, Vorgang, Unterlage, Ereignis, Ausgang, PushAbo, select  # noqa: E402
from main import app  # noqa: E402

ALLE = []


def gate(name):
    def deko(f):
        ALLE.append((name, f))
        return f
    return deko


# ------------------------------------------------------------ Werkzeuge

def pdf_mit_text(zeilen: list[str]) -> bytes:
    p = io.BytesIO()
    c = canvas.Canvas(p, pagesize=A4)
    y = 800
    for z in zeilen:
        c.drawString(60, y, z)
        y -= 18
    c.save()
    return p.getvalue()


LISTE = pdf_mit_text([
    "Unterlagenliste - Musterbank AG",
    "[ ] Gehaltsnachweise der letzten 3 Monate",
    "[ ] Personalausweis (Kopie Vorder- und Rueckseite)",
    "[ ] Aktueller Grundbuchauszug",
    "[ ] Flurkarte / Lageplan",
    "[ ] Wohnflaechenberechnung",
    "[ ] Grundrisse aller Geschosse",
    "[ ] Kaufvertragsentwurf vom Notar",
    "[ ] Energieausweis",
    "[ ] Kostenvoranschlaege Handwerker fuer Modernisierung",
])

PUSH_GESENDET: list[tuple] = []


def push_attrappe(abo, nutzlast):
    PUSH_GESENDET.append((abo.inhaber_art, abo.inhaber_id, nutzlast))


push._sender = push_attrappe


def foto(breite=1400, hoehe=1900, scharf=True, hell=200) -> bytes:
    im = Image.new("L", (breite, hoehe), 90)
    d = ImageDraw.Draw(im)
    d.rectangle([120, 150, breite - 120, hoehe - 150], fill=hell)
    for i in range(20):
        y = 220 + i * 70
        d.rectangle([180, y, breite - 300 - (i % 4) * 90, y + 14], fill=30)
        d.rectangle([180, y + 28, breite - 500, y + 36], fill=60)
    if not scharf:
        from PIL import ImageFilter
        im = im.filter(ImageFilter.GaussianBlur(12))
    p = io.BytesIO()
    im.convert("RGB").save(p, format="JPEG", quality=85)
    return p.getvalue()


class Lauf:
    """Ein Durchlauf mit Berater- und Kundenclient."""
    def __init__(self):
        self.c = TestClient(app, base_url="http://testserver")
        self.c.__enter__()
        self.berater = TestClient(app, base_url="http://testserver")
        self.kunde = TestClient(app, base_url="http://testserver")
        r = self.berater.post("/berater/anmelden", data={"email": "berater@example.org", "passwort": "test1234"}, follow_redirects=False)
        assert r.status_code == 303, "Beraterlogin"

    def s(self):
        return db.sitzung()

    def kunde_anlegen(self, email="anna@example.org", herkunft="makler"):
        r = self.berater.post("/berater/kunde/neu", data={"vorname": "Anna", "nachname": "Muster", "email": email,
                                                           "telefon": "0170", "herkunft": herkunft}, follow_redirects=False)
        assert r.status_code == 303, r.text
        self.vid = int(r.headers["location"].split("/")[-1].split("?")[0])
        with self.s() as s:
            k = s.scalar(select(Kunde).where(Kunde.email == email))
            self.kid = k.id
            self.link = k.anmeldelink
        return self.vid

    def kunde_einloggen(self):
        r = self.kunde.get(f"/k/{self.link}", follow_redirects=False)
        assert r.status_code == 303 and "/app/start" in r.headers["location"], r.headers
        r = self.kunde.post("/app/start", data={"beschaeftigung": "angestellt", "netto_1": 3200, "netto_2": 3150, "netto_3": 3300}, follow_redirects=False)
        assert r.status_code == 303

    def liste_hochladen(self, modernisierung=True, betrag=150000):
        self.berater.post(f"/berater/vorgang/{self.vid}/daten", data={"bezeichnung": "Musterweg 1, Berlin", "bank": "",
                          "zins_gueltig_bis": (date.today() + timedelta(days=20)).isoformat(),
                          "modernisierung": "ja" if modernisierung else "nein", "modernisierung_betrag": str(betrag)})
        r = self.berater.post(f"/berater/vorgang/{self.vid}/liste", files={"datei": ("liste.pdf", LISTE, "application/pdf")}, follow_redirects=False)
        assert r.status_code == 303, r.text

    def unterlagen(self):
        with self.s() as s:
            return s.scalars(select(Unterlage).where(Unterlage.vorgang_id == self.vid).order_by(Unterlage.reihenfolge)).all()

    def unterlage(self, typ):
        return next(u for u in self.unterlagen() if u.katalog_typ == typ)


# ------------------------------------------------------------------ Gates

@gate("der-dienst-meldet-gesund-und-version-mit-abdruck")
def g_gesund():
    c = TestClient(app)
    with c:
        assert c.get("/gesund").json()["ok"] is True
        v = c.get("/version").json()
        assert v["name"] == "AKTE" and len(v["abdruck"]) == 16


@gate("der-katalog-ordnet-bankpositionen-per-schlagwort-zu")
def g_katalog():
    assert katalog.zuordnen_heuristisch("Aktueller Grundbuchauszug")[0] == "grundbuchauszug"
    assert katalog.zuordnen_heuristisch("Wohnflaechenberechnung nach WoFlV")[0] == "wohnflaechenberechnung"
    assert katalog.zuordnen_heuristisch("Gehaltsabrechnungen der letzten 3 Monate")[0] == "gehaltsnachweis"
    assert katalog.zuordnen_heuristisch("Irgendwas voellig anderes")[0] == "sonstiges"
    assert katalog.typ("grundbuchauszug").kritisch and katalog.typ("wohnflaechenberechnung").kritisch and katalog.typ("grundriss").kritisch
    assert not katalog.typ("kaufvertrag").kritisch


@gate("die-beteiligtenrollen-haengen-an-modernisierung-und-100k-grenze")
def g_rollen():
    assert katalog.rollen_fuer_vorgang(False, None) == ["makler", "verkaeufer", "notar"]
    assert katalog.rollen_fuer_vorgang(True, 50000) == ["makler", "verkaeufer", "notar", "handwerker"]
    assert katalog.rollen_fuer_vorgang(True, 150000) == ["makler", "verkaeufer", "notar", "architekt", "handwerker"]


@gate("der-berater-legt-einen-kunden-an-und-die-einstiegsmail-geht-raus")
def g_kunde_anlegen():
    L = Lauf()
    L.kunde_anlegen(email="einstieg@example.org")
    with L.s() as s:
        m = s.scalar(select(Ausgang).where(Ausgang.an == "einstieg@example.org"))
        assert m is not None and "/k/" in m.text and "drei Nettogeh" in m.text, m.text if m else "keine Mail"
        k = s.get(Kunde, L.kid)
        assert k.herkunft == "makler" and k.anmeldelink


@gate("die-homepage-buchung-legt-den-kunden-nur-mit-schluessel-an")
def g_buchung():
    c = TestClient(app)
    with c:
        assert c.post("/api/buchung", data={"name": "Max Web", "email": "web@example.org", "schluessel": "falsch"}).status_code == 403
        r = c.post("/api/buchung", data={"name": "Max Web", "email": "web@example.org", "telefon": "1", "schluessel": "buchung-geheim"})
        assert r.status_code == 200 and r.json()["ok"], r.text
    with db.sitzung() as s:
        k = s.scalar(select(Kunde).where(Kunde.email == "web@example.org"))
        assert k.vorname == "Max" and k.nachname == "Web" and k.herkunft == "homepage"


@gate("der-kunde-kommt-per-link-rein-und-traegt-drei-nettogehaelter-ein")
def g_onboarding():
    L = Lauf()
    L.kunde_anlegen(email="onboarding@example.org")
    L.kunde_einloggen()
    with L.s() as s:
        k = s.get(Kunde, L.kid)
        assert k.onboarding_am and k.netto_2 == 3150 and k.beschaeftigung == "angestellt"
        # Berater wurde informiert
        assert s.scalar(select(Ereignis).where(Ereignis.art == "meldung_berater", Ereignis.berater_id == 1)) is not None
    r = L.kunde.get("/app")
    assert r.status_code == 200 and "bereitet dein Angebot vor" in r.text


@gate("ein-abgelaufener-anmeldelink-wird-abgewiesen")
def g_link_abgelaufen():
    L = Lauf()
    L.kunde_anlegen(email="alt@example.org")
    with L.s() as s:
        k = s.get(Kunde, L.kid)
        k.anmeldelink_bis = db.jetzt() - timedelta(days=1)
        s.commit()
    r = L.kunde.get(f"/k/{L.link}", follow_redirects=False)
    assert r.status_code == 200 and "abgelaufen" in r.text
    assert L.kunde.get("/app", follow_redirects=False).status_code == 303


@gate("die-unterlagenliste-wird-gelesen-zugeordnet-und-der-kunde-bekommt-den-push")
def g_liste():
    L = Lauf()
    L.kunde_anlegen(email="liste@example.org")
    L.kunde_einloggen()
    PUSH_GESENDET.clear()
    with L.s() as s:
        push.abo_speichern(s, "kunde", L.kid, {"endpoint": "https://push.example/1", "keys": {"p256dh": "x", "auth": "y"}})
        s.commit()
    L.liste_hochladen()
    typen = {u.katalog_typ for u in L.unterlagen()}
    for erwartet in ("gehaltsnachweis", "personalausweis", "grundbuchauszug", "flurkarte", "wohnflaechenberechnung", "grundriss", "kaufvertrag", "energieausweis", "handwerkerangebote"):
        assert erwartet in typen, f"{erwartet} fehlt in {typen}"
    assert any(p[0] == "kunde" and "Unterlagenliste ist da" in p[2] for p in PUSH_GESENDET), PUSH_GESENDET
    with L.s() as s:
        v = s.get(Vorgang, L.vid)
        assert v.status == "sammeln"
        assert all(u.kritisch for u in v.unterlagen if u.katalog_typ in ("grundbuchauszug", "wohnflaechenberechnung", "grundriss"))


@gate("der-kunde-wird-erst-nach-den-beteiligten-gefragt-und-dann-gewarnt")
def g_beteiligte():
    L = Lauf()
    L.kunde_anlegen(email="beteiligte@example.org")
    L.kunde_einloggen()
    L.liste_hochladen(modernisierung=True, betrag=150000)
    r = L.kunde.get("/app", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/app/beteiligte"
    r = L.kunde.get("/app/beteiligte")
    assert "Architekt" in r.text and "Handwerker" in r.text and "Notar" in r.text
    # Nur Makler angeben -> Warnung mit Beschaffungsangebot
    r = L.kunde.post("/app/beteiligte", data={"makler_name": "Herr Makler", "makler_email": "makler@example.org"}, follow_redirects=False)
    assert r.status_code == 303 and "beschaffung?warnung=1" in r.headers["location"], r.headers
    r = L.kunde.get("/app/beschaffung?warnung=1")
    assert "dringende Empfehlung" in r.text and "unterschreib" in r.text.lower()
    r = L.kunde.get("/app")
    assert "Ansprechpartner fehlen" in r.text and "Verkaeufer" in r.text


@gate("ohne-modernisierung-werden-architekt-und-handwerker-nicht-abgefragt")
def g_beteiligte_ohne_modernisierung():
    L = Lauf()
    L.kunde_anlegen(email="ohnemod@example.org")
    L.kunde_einloggen()
    L.liste_hochladen(modernisierung=False, betrag=0)
    r = L.kunde.get("/app/beteiligte")
    assert "Architekt" not in r.text and "Handwerker" not in r.text and "Makler" in r.text


@gate("der-beschaffungsauftrag-mit-app-unterschrift-erzeugt-pdf-vollmacht-und-sperrt-die-unterlagen")
def g_beschaffung():
    L = Lauf()
    L.kunde_anlegen(email="auftrag@example.org")
    L.kunde_einloggen()
    with L.s() as s:
        b = s.get(db.Berater, 1)
        b.preis_beschaffung = 25.0
        s.commit()
    L.liste_hochladen()
    L.kunde.post("/app/beteiligte", data={})
    gb, fk = L.unterlage("grundbuchauszug"), L.unterlage("flurkarte")
    png = io.BytesIO()
    Image.new("RGBA", (300, 100), (0, 0, 0, 0)).save(png, format="PNG")
    import base64
    unterschrift = "data:image/png;base64," + base64.b64encode(png.getvalue()).decode()
    r = L.kunde.post("/app/beschaffung", data={"unterlage": [str(gb.id), str(fk.id)], "unterschrift": unterschrift}, follow_redirects=False)
    assert r.status_code == 303 and "auftrag=1" in r.headers["location"], r.headers
    with L.s() as s:
        v = s.get(Vorgang, L.vid)
        assert v.vollmacht_vorhanden and v.vollmacht_berater_datei.endswith(".pdf")
        assert open(v.vollmacht_berater_datei, "rb").read()[:5] == b"%PDF-"
        vm = s.scalar(select(db.Vollmacht).where(db.Vollmacht.vorgang_id == v.id))
        assert vm.betrag == 50.0
        st = {u.katalog_typ: u.status for u in v.unterlagen}
        assert st["grundbuchauszug"] == "beauftragt" and st["flurkarte"] == "beauftragt" and st["kaufvertrag"] == "fehlt"
    # Ohne Unterschrift kein Auftrag
    r = L.kunde.post("/app/beschaffung", data={"unterlage": [str(gb.id)], "unterschrift": ""}, follow_redirects=False)
    assert "fehler=1" in r.headers["location"]


@gate("der-berater-darf-nur-mit-vollmacht-fuer-den-kunden-hochladen")
def g_berater_upload_vollmacht():
    L = Lauf()
    L.kunde_anlegen(email="vollmacht@example.org")
    L.kunde_einloggen()
    L.liste_hochladen()
    u = L.unterlage("kaufvertrag")
    pdf = pdf_mit_text(["Kaufvertragsentwurf", "Kaufpreis 400.000 EUR", "Muster"])
    r = L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/{u.id}/upload", files={"datei": ("k.pdf", pdf, "application/pdf")})
    assert r.status_code == 403, r.status_code
    # Schriftliche Vollmacht hinterlegen -> Upload geht
    r = L.berater.post(f"/berater/vorgang/{L.vid}/vollmacht", files={"datei": ("v.pdf", pdf_mit_text(["Vollmacht"]), "application/pdf")}, follow_redirects=False)
    assert r.status_code == 303
    r = L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/{u.id}/upload", files={"datei": ("k.pdf", pdf, "application/pdf")}, follow_redirects=False)
    assert r.status_code == 303
    u = L.unterlage("kaufvertrag")
    assert u.status == "wartet_freigabe" and u.hochgeladen_von == "berater"  # ohne KI: manuelle Pruefung


@gate("kundenupload-ohne-ki-landet-bei-der-beraterfreigabe-und-der-berater-wird-informiert")
def g_upload_kunde():
    L = Lauf()
    L.kunde_anlegen(email="upload@example.org")
    L.kunde_einloggen()
    L.liste_hochladen()
    L.kunde.post("/app/beteiligte", data={})
    u = L.unterlage("personalausweis")
    pdf = pdf_mit_text(["Personalausweis", "Anna Muster", "gueltig bis 2030"])
    r = L.kunde.post(f"/app/unterlage/{u.id}/upload", files=[("dateien", ("ausweis.pdf", pdf, "application/pdf"))], follow_redirects=False)
    assert r.status_code == 303 and "geprueft=1" in r.headers["location"]
    u = L.unterlage("personalausweis")
    assert u.status == "wartet_freigabe" and u.datei and u.dateiname.endswith(".pdf"), (u.status, u.dateiname)
    with L.s() as s:
        assert s.scalar(select(Ereignis).where(Ereignis.vorgang_id == L.vid, Ereignis.art == "meldung_berater", Ereignis.text.like("Unterlage hochgeladen%"))) is not None
        assert s.scalar(select(Ausgang).where(Ausgang.an == "berater@example.org", Ausgang.betreff.like("%Unterlage hochgeladen%"))) is not None


@gate("ein-bild-pdf-ohne-text-wird-als-foto-abgelehnt-mit-fehlerliste")
def g_foto_pdf_abgelehnt():
    L = Lauf()
    L.kunde_anlegen(email="fotopdf@example.org")
    L.kunde_einloggen()
    L.liste_hochladen()
    L.kunde.post("/app/beteiligte", data={})
    u = L.unterlage("gehaltsnachweis")
    p = io.BytesIO()
    Image.new("RGB", (800, 1100), "white").save(p, format="PDF")
    r = L.kunde.post(f"/app/unterlage/{u.id}/upload", files=[("dateien", ("foto.pdf", p.getvalue(), "application/pdf"))], follow_redirects=False)
    assert r.status_code == 303
    u = L.unterlage("gehaltsnachweis")
    assert u.status == "abgelehnt" and any("nur ein Bild" in f for f in u.fehler), (u.status, u.fehler)
    r = L.kunde.get(f"/app/unterlage/{u.id}")
    assert "Das muss noch behoben werden" in r.text


@gate("der-scanner-lehnt-unscharfe-und-dunkle-fotos-mit-konkretem-grund-ab")
def g_scanner_qualitaet():
    assert scanner.qualitaet(foto()).ok, scanner.qualitaet(foto()).maengel
    b = scanner.qualitaet(foto(scharf=False))
    assert not b.ok and any("unscharf" in m for m in b.maengel), b
    b = scanner.qualitaet(foto(hell=40))
    assert not b.ok and any("dunkel" in m for m in b.maengel), b
    b = scanner.qualitaet(b"kein bild")
    assert not b.ok


@gate("mehrere-gute-fotos-werden-ein-pdf-und-schlechte-seiten-werden-benannt")
def g_scanner_pdf():
    pdf, maengel = scanner.fotos_zu_pdf([foto(), foto()])
    assert pdf and pdf[:5] == b"%PDF-" and maengel == [[], []]
    from pypdf import PdfReader
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 2
    pdf, maengel = scanner.fotos_zu_pdf([foto(), foto(scharf=False)])
    assert pdf is None and maengel[0] == [] and maengel[1]


@gate("fotoupload-in-der-app-wird-gescannt-und-geprueft")
def g_fotoupload():
    L = Lauf()
    L.kunde_anlegen(email="fotos@example.org")
    L.kunde_einloggen()
    L.liste_hochladen()
    L.kunde.post("/app/beteiligte", data={})
    u = L.unterlage("objektfotos") if "objektfotos" in {x.katalog_typ for x in L.unterlagen()} else None
    if u is None:
        L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/neu", data={"bezeichnung": "Fotos vom Objekt", "katalog_typ": "objektfotos"})
        u = L.unterlage("objektfotos")
    r = L.kunde.post(f"/app/unterlage/{u.id}/upload", files=[("dateien", ("a.jpg", foto(), "image/jpeg")), ("dateien", ("b.jpg", foto(), "image/jpeg"))], follow_redirects=False)
    assert r.status_code == 303 and "geprueft=1" in r.headers["location"], r.headers
    u = L.unterlage("objektfotos")
    assert u.datei.endswith(".pdf") and open(u.datei, "rb").read()[:5] == b"%PDF-"
    # Schlechtes Foto -> Fehlerliste mit Seitenangabe, kein Upload
    r = L.kunde.post(f"/app/unterlage/{u.id}/upload", files=[("dateien", ("a.jpg", foto(), "image/jpeg")), ("dateien", ("b.jpg", foto(scharf=False), "image/jpeg"))], follow_redirects=False)
    assert "fehler=scan" in r.headers["location"]
    u = L.unterlage("objektfotos")
    assert any(f.startswith("Foto 2:") for f in u.fehler), u.fehler


@gate("kritische-unterlagen-brauchen-die-beraterfreigabe-und-ablehnung-erzeugt-fehlerliste")
def g_freigabe():
    L = Lauf()
    L.kunde_anlegen(email="freigabe@example.org")
    L.kunde_einloggen()
    L.liste_hochladen()
    L.kunde.post("/app/beteiligte", data={})
    u = L.unterlage("grundbuchauszug")
    pdf = pdf_mit_text(["Grundbuch von Berlin Blatt 123", "Abteilung I II III", "Amtsgericht Mitte"])
    L.kunde.post(f"/app/unterlage/{u.id}/upload", files=[("dateien", ("gb.pdf", pdf, "application/pdf"))])
    assert L.unterlage("grundbuchauszug").status == "wartet_freigabe"
    L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/{u.id}", data={"aktion": "ablehnen", "kommentar": "Auszug ist aelter als 3 Monate"})
    u = L.unterlage("grundbuchauszug")
    assert u.status == "abgelehnt" and u.fehler[0].startswith("Berater: Auszug")
    L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/{u.id}", data={"aktion": "freigeben", "kommentar": ""})
    assert L.unterlage("grundbuchauszug").status == "akzeptiert"


@gate("die-makler-mail-ist-ein-mailto-link-und-die-nachfrage-kommt-nach-zwei-tagen")
def g_makler():
    L = Lauf()
    L.kunde_anlegen(email="makler@example.org")
    L.kunde_einloggen()
    L.liste_hochladen()
    L.kunde.post("/app/beteiligte", data={"makler_name": "Frau Makler", "makler_email": "fm@example.org"})
    u = L.unterlage("energieausweis")
    r = L.kunde.get(f"/app/unterlage/{u.id}")
    assert "mailto:fm@example.org?" in r.text and "Ich habe die Mail gesendet" in r.text
    L.kunde.post(f"/app/unterlage/{u.id}/makler-gesendet", data={})
    u = L.unterlage("energieausweis")
    assert u.status == "angefragt" and u.nachfrage_am
    # Nachfrage noch nicht faellig
    with L.s() as s:
        assert not any(x.startswith("nachfrage_makler") for x in zeitplan.lauf(s))
    with L.s() as s:
        for x in s.scalars(select(Unterlage).where(Unterlage.vorgang_id == L.vid, Unterlage.status == "angefragt")):
            x.nachfrage_am = db.jetzt() - timedelta(hours=1)
        s.commit()
    PUSH_GESENDET.clear()
    with L.s() as s:
        push.abo_speichern(s, "kunde", L.kid, {"endpoint": "https://push.example/m", "keys": {"p256dh": "x", "auth": "y"}})
        s.commit()
        getan = zeitplan.lauf(s)
    assert f"nachfrage_makler:{L.vid}" in getan, getan
    assert any("Antwort vom Makler" in p[2] for p in PUSH_GESENDET)
    with L.s() as s:  # kein zweites Mal
        assert not any(x.startswith("nachfrage_makler") for x in zeitplan.lauf(s))
    r = L.kunde.get("/app/nachfrage")
    assert "anmahnen" in r.text.lower() and "Ich habe die Mahnung gesendet" in r.text


@gate("zinsdatum-erinnerungen-ein-tag-vorher-woechentlich-wenn-es-fehlt-und-nach-ablauf")
def g_zins():
    L = Lauf()
    L.kunde_anlegen(email="zins@example.org")
    L.kunde_einloggen()
    heute = date.today()
    with L.s() as s:
        v = s.get(Vorgang, L.vid)
        v.status = "sammeln"
        s.commit()
        getan = zeitplan.lauf(s, heute)
        assert f"zinsdatum_fehlt:{L.vid}" in getan, getan
        assert f"zinsdatum_fehlt:{L.vid}" not in zeitplan.lauf(s, heute)              # nicht zweimal am Tag
        assert f"zinsdatum_fehlt:{L.vid}" not in zeitplan.lauf(s, heute + timedelta(days=3))
        assert f"zinsdatum_fehlt:{L.vid}" in zeitplan.lauf(s, heute + timedelta(days=7))  # woechentlich
        v = s.get(Vorgang, L.vid)
        v.zins_gueltig_bis = heute + timedelta(days=1)
        v.zins_wochen_erinnert_am = None  # wie beim Setzen ueber die Beraterseite
        s.commit()
        assert f"zins_morgen:{L.vid}" in zeitplan.lauf(s, heute)
        assert f"zins_morgen:{L.vid}" not in zeitplan.lauf(s, heute)
        assert f"zins_abgelaufen:{L.vid}" in zeitplan.lauf(s, heute + timedelta(days=9))
        assert f"zins_abgelaufen:{L.vid}" not in zeitplan.lauf(s, heute + timedelta(days=10))
        assert f"zins_abgelaufen:{L.vid}" in zeitplan.lauf(s, heute + timedelta(days=16))
        # Berater bekam Mails
        assert s.scalar(select(Ausgang).where(Ausgang.betreff.like("%Zinskondition laeuft morgen ab%"))) is not None
        assert s.scalar(select(Ausgang).where(Ausgang.betreff.like("%Zinskondition abgelaufen%"))) is not None
        assert s.scalar(select(Ausgang).where(Ausgang.betreff.like("%Zinsdatum fehlt%"))) is not None


@gate("wer-hilfe-ablehnt-sieht-den-haftungshinweis-und-bekommt-woechentlich-den-push")
def g_hilfe_abgelehnt():
    L = Lauf()
    L.kunde_anlegen(email="ablehnen@example.org")
    L.kunde_einloggen()
    L.liste_hochladen()
    L.kunde.post("/app/beteiligte", data={})
    r = L.kunde.post("/app/beschaffung/ablehnen", follow_redirects=True)
    assert "keine Haftung" in r.text
    heute = date.today()
    with L.s() as s:
        assert f"hilfe_erinnerung:{L.vid}" not in zeitplan.lauf(s, heute)
        assert f"hilfe_erinnerung:{L.vid}" in zeitplan.lauf(s, heute + timedelta(days=7))
        assert f"hilfe_erinnerung:{L.vid}" not in zeitplan.lauf(s, heute + timedelta(days=8))
        assert s.scalar(select(Ausgang).where(Ausgang.betreff.like("%doch helfen%"))) is not None


@gate("export-geht-erst-nach-akzeptanz-aller-unterlagen-und-freigabe-des-kunden")
def g_export():
    L = Lauf()
    L.kunde_anlegen(email="export@example.org")
    L.kunde_einloggen()
    L.liste_hochladen(modernisierung=False)
    L.kunde.post("/app/beteiligte", data={})
    assert L.berater.get(f"/berater/vorgang/{L.vid}/export.zip").status_code == 409
    # Alles bis auf eine Unterlage nicht erforderlich, eine hochladen und freigeben
    us = L.unterlagen()
    for u in us[1:]:
        L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/{u.id}", data={"aktion": "nicht_erforderlich"})
    u0 = us[0]
    L.kunde.post(f"/app/unterlage/{u0.id}/upload", files=[("dateien", ("x.pdf", pdf_mit_text(["Gehaltsabrechnung Anna Muster", "Netto 3200"]), "application/pdf"))])
    L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/{u0.id}", data={"aktion": "freigeben"})
    assert L.berater.get(f"/berater/vorgang/{L.vid}/export.zip").status_code == 409  # Freigabe fehlt
    r = L.kunde.get("/app")
    assert "Unterlagen freigeben" in r.text
    L.kunde.post("/app/freigabe")
    r = L.berater.get(f"/berater/vorgang/{L.vid}/export.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(r.content))
    namen = z.namelist()
    assert "00_inhalt.txt" in namen and any(n.startswith("01_") and n.endswith(".pdf") for n in namen), namen
    with L.s() as s:
        assert s.get(Vorgang, L.vid).status == "exportiert"


@gate("die-schriftliche-bestaetigung-des-beraters-ersetzt-die-app-freigabe")
def g_freigabe_schriftlich():
    L = Lauf()
    L.kunde_anlegen(email="schriftlich@example.org")
    L.kunde_einloggen()
    L.liste_hochladen(modernisierung=False)
    us = L.unterlagen()
    for u in us[1:]:
        L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/{u.id}", data={"aktion": "nicht_erforderlich"})
    L.berater.post(f"/berater/vorgang/{L.vid}/unterlage/{us[0].id}", data={"aktion": "erledigt"})
    L.berater.post(f"/berater/vorgang/{L.vid}/freigabe-schriftlich", data={"bestaetigt": "ja"})
    with L.s() as s:
        assert s.get(Vorgang, L.vid).export_moeglich


@gate("ein-neues-zinsdatum-nach-ablauf-informiert-den-kunden-und-setzt-erinnerungen-zurueck")
def g_neues_angebot():
    L = Lauf()
    L.kunde_anlegen(email="neu@example.org")
    L.kunde_einloggen()
    L.liste_hochladen()
    with L.s() as s:
        v = s.get(Vorgang, L.vid)
        v.zins_wochen_erinnert_am = date.today()
        s.commit()
    L.berater.post(f"/berater/vorgang/{L.vid}/daten", data={"bezeichnung": "x", "bank": "Bank B", "zins_gueltig_bis": (date.today() + timedelta(days=30)).isoformat(), "modernisierung": "nein", "modernisierung_betrag": ""})
    with L.s() as s:
        v = s.get(Vorgang, L.vid)
        assert v.zins_wochen_erinnert_am is None and v.bank == "Bank B"
        assert s.scalar(select(Ausgang).where(Ausgang.an == "neu@example.org", Ausgang.betreff == "Neue Zinskondition")) is not None


@gate("die-vertretung-sieht-die-vorgaenge-des-vertretenen-beraters")
def g_vertretung():
    L = Lauf()
    L.kunde_anlegen(email="vertretung@example.org")
    with L.s() as s:
        import auth
        v2 = db.Berater(name="Vertreter", email="vertreter@example.org", passwort_hash=auth.passwort_hash("pw"))
        s.add(v2)
        s.flush()
        s.get(db.Berater, 1).vertreter_id = v2.id
        s.commit()
    c = TestClient(app)
    with c:
        c.post("/berater/anmelden", data={"email": "vertreter@example.org", "passwort": "pw"})
        r = c.get("/berater")
        assert "vertretung@example.org" in r.text and "(Vertretung)" in r.text
        assert c.get(f"/berater/vorgang/{L.vid}").status_code == 200


@gate("das-ereignisprotokoll-haelt-upload-warnung-und-freigabe-fest")
def g_logbuch():
    with db.sitzung() as s:
        arten = {e.art for e in s.scalars(select(Ereignis)).all()}
    for a in ("kunde_angelegt", "einstiegsmail", "onboarding", "liste_hochgeladen", "upload", "hilfe_abgelehnt",
              "beschaffungsauftrag", "beraterfreigabe", "beraterablehnung", "freigabe_kunde", "export", "makler_mail", "push"):
        assert a in arten, f"{a} fehlt im Logbuch"


@gate("ohne-ki-schluessel-liefert-die-pruefung-manuell-und-die-liste-heuristik")
def g_ki_rueckfall():
    assert not E.KI_AKTIV
    e = ki.liste_lesen(LISTE)
    assert e["quelle"] == "heuristik" and len(e["positionen"]) >= 8
    p = ki.unterlage_pruefen(pdf_mit_text(["Grundbuch von Berlin Blatt 1234", "Abteilung I, II, III", "Amtsgericht Mitte"]), "grundbuchauszug", "Grundbuchauszug", "Muster")
    assert p["passt"] is None and p["quelle"] == "manuell" and p["dateiname"].endswith("-muster.pdf")
    p = ki.unterlage_pruefen(b"kein pdf", "grundbuchauszug", "Grundbuchauszug", "Muster")
    assert p["passt"] is False


# ------------------------------------------------------------------- Lauf

def main() -> int:
    nur = os.environ.get("AKTE_NUR")
    db.verbinden(os.environ["DATABASE_URL"])
    with TestClient(app):
        pass  # Startup: Berater anlegen
    rot = 0
    for name, f in ALLE:
        if nur and nur not in name:
            continue
        try:
            f()
            print(f"GRUEN  {name}")
        except Exception:  # noqa: BLE001
            rot += 1
            print(f"ROT    {name}")
            traceback.print_exc()
    print(f"\nERGEBNIS: {'ALLE GRUEN' if not rot else str(rot) + ' ROT'} ({len(ALLE)} Gates)")
    return 1 if rot else 0


if __name__ == "__main__":
    sys.exit(main())
