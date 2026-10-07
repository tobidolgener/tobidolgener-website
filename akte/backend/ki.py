"""KI-Funktionen: Unterlagenliste lesen, Unterlage pruefen und benennen.

Ohne ANTHROPIC_API_KEY arbeitet das Modul mit Rueckfaellen (Schlagworte, PDF-Metadaten),
und jede Unterlage wandert zur manuellen Pruefung an den Berater.
"""
import base64
import io
import json
import re

import einstellungen as E
import katalog

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

# Pruefregeln je Katalogtyp. Werden im Entwicklungsprozess mit dem Berater verfeinert.
PRUEFREGELN = {
    "gehaltsnachweis": "Drei aufeinanderfolgende Monatsabrechnungen, nicht aelter als 3 Monate. Name des Kunden, Arbeitgeber, Brutto und Netto lesbar. Keine Fotos.",
    "personalausweis": "Vorder- und Rueckseite, gueltig, alle Angaben lesbar.",
    "kontoauszuege": "Lueckenlos die letzten 3 Monate, Kontoinhaber lesbar, Gehaltseingaenge sichtbar.",
    "eigenkapitalnachweis": "Aktueller Stand (max. 4 Wochen alt), Inhaber lesbar, Betrag erkennbar.",
    "steuerbescheid": "Vollstaendiger Bescheid mit allen Seiten, Steuerjahr erkennbar.",
    "bwa": "BWA mit Summen- und Saldenliste, Zeitraum erkennbar, Jahresabschluesse vollstaendig.",
    "grundbuchauszug": "Aktueller Auszug (max. 3 Monate), alle Abteilungen I bis III, Bestandsverzeichnis, Blattnummer und Amtsgericht lesbar.",
    "flurkarte": "Flurstueck und Gemarkung erkennbar, Massstab angegeben, Objekt markiert.",
    "baulastenverzeichnis": "Auszug oder Negativbescheinigung mit Datum und Behoerde.",
    "grundriss": "Alle Geschosse, Raumbezeichnungen, Masse oder Massstab, lesbar.",
    "wohnflaechenberechnung": "Berechnung nach WoFlV, je Raum, mit Summe; Ersteller erkennbar.",
    "energieausweis": "Gueltig (Ausstellungsdatum + 10 Jahre), Objektadresse stimmt, alle Seiten.",
    "kaufvertrag": "Vollstaendiger Vertrag oder Entwurf mit Kaufpreis, Parteien und Objekt.",
    "urkunden_abteilung_2": "Bewilligungsurkunde zur jeweiligen Eintragung, vollstaendig.",
    "kostenaufstellung_architekt": "Nach Gewerken gegliedert, mit Summe, Ersteller mit Qualifikation.",
    "handwerkerangebote": "Firmierung, Datum, Leistungsbeschreibung, Netto- und Bruttosumme.",
    "objektfotos": "Aussenansicht und Innenraeume erkennbar. Fotos sind hier erwuenscht.",
    "vollmacht_verkaeufer": "Vollmacht aus der App, Name des Verkaeufers und Unterschrift vorhanden.",
}

SYSTEM_PRUEFUNG = (
    "Du pruefst Unterlagen fuer eine Baufinanzierung in Deutschland, so wie eine Bank sie annimmt. "
    "Du antwortest nur mit dem geforderten JSON. Sei streng bei Lesbarkeit, Vollstaendigkeit und Aktualitaet, "
    "aber nenne jeden Mangel konkret und loesbar, damit der Kunde weiss, was er nachliefern muss. "
    "Fotos von Dokumenten (schief, Schatten, abgeschnitten) akzeptiert die Bank nicht, ausser bei Objektfotos."
)

SCHEMA_LISTE = {
    "type": "object",
    "properties": {
        "bank": {"type": "string"},
        "positionen": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "bezeichnung": {"type": "string"},
                    "katalog_typ": {"type": "string", "enum": [t.schluessel for t in katalog.TYPEN]},
                    "sicher": {"type": "boolean"},
                },
                "required": ["bezeichnung", "katalog_typ", "sicher"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["bank", "positionen"],
    "additionalProperties": False,
}

SCHEMA_PRUEFUNG = {
    "type": "object",
    "properties": {
        "passt": {"type": "boolean"},
        "erkannter_typ": {"type": "string", "enum": [t.schluessel for t in katalog.TYPEN]},
        "fehler": {"type": "array", "items": {"type": "string"}},
        "dateiname": {"type": "string"},
        "zusammenfassung": {"type": "string"},
    },
    "required": ["passt", "erkannter_typ", "fehler", "dateiname", "zusammenfassung"],
    "additionalProperties": False,
}

_client = None


def _klient():
    global _client
    if _client is None and E.KI_AKTIV and anthropic is not None:
        _client = anthropic.Anthropic()
    return _client


def _anfrage(system: str, inhalt: list, schema: dict) -> dict | None:
    """Ein Aufruf mit strukturierter Antwort. None bei Fehler oder Ablehnung."""
    c = _klient()
    if c is None:
        return None
    params = dict(
        model=E.KI_MODELL, max_tokens=4000, system=system,
        messages=[{"role": "user", "content": inhalt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    try:
        try:
            # Server-seitiger Rueckfall bei Sicherheitsablehnung (Standardroute)
            antwort = c.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params)
        except TypeError:
            antwort = c.messages.create(**params)
        if antwort.stop_reason == "refusal":
            return None
        text = next((b.text for b in antwort.content if b.type == "text"), "")
        return json.loads(text)
    except Exception:  # noqa: BLE001 - KI-Ausfall darf den Ablauf nicht stoppen
        return None


def _pdf_block(pdf_bytes: bytes) -> dict:
    return {"type": "document",
            "source": {"type": "base64", "media_type": "application/pdf",
                       "data": base64.standard_b64encode(pdf_bytes).decode()}}


def pdf_text(pdf_bytes: bytes, max_seiten: int = 20) -> tuple[str, int]:
    """Text und Seitenzahl aus einem PDF. ("", 0) wenn unlesbar."""
    if PdfReader is None:
        return "", 0
    try:
        leser = PdfReader(io.BytesIO(pdf_bytes))
        seiten = len(leser.pages)
        text = "\n".join((leser.pages[i].extract_text() or "") for i in range(min(seiten, max_seiten)))
        return text, seiten
    except Exception:  # noqa: BLE001
        return "", 0


# ------------------------------------------------------------- Liste lesen

def liste_lesen(pdf_bytes: bytes) -> dict:
    """Europace-Unterlagenliste -> Positionen mit Katalogzuordnung.

    Rueckgabe: {"bank": str, "positionen": [{"bezeichnung", "katalog_typ", "sicher"}], "quelle": "ki"|"heuristik"}
    """
    beschreibung = "\n".join(f"- {t.schluessel}: {t.name}" for t in katalog.TYPEN)
    system = (
        "Du liest Unterlagenlisten aus Europace fuer Baufinanzierungen. Extrahiere jede geforderte Unterlage "
        "als eigene Position (Mehrfachnennungen wie 'Gehaltsnachweise der letzten 3 Monate' bleiben EINE Position). "
        "Ordne jede Position genau einem Katalogtyp zu. Setze sicher=false, wenn die Zuordnung unklar ist. "
        "Erkenne die Bank, falls genannt.\n\nKatalog:\n" + beschreibung
    )
    ergebnis = _anfrage(system, [_pdf_block(pdf_bytes), {"type": "text", "text": "Lies die Unterlagenliste."}], SCHEMA_LISTE)
    if ergebnis and ergebnis.get("positionen"):
        ergebnis["quelle"] = "ki"
        return ergebnis
    # Rueckfall: Zeilen aus dem PDF-Text, Schlagwortzuordnung
    text, _ = pdf_text(pdf_bytes)
    positionen = []
    for zeile in text.splitlines():
        z = re.sub(r"^(\s|[\-\*\u2022\u25a1\u2610\u2611\u2612]|\[\s*[xX]?\s*\]|\(\s*[xX]?\s*\)|\d+[\.\)])+", "", zeile).strip()
        if len(z) < 4 or len(z) > 160:
            continue
        schluessel, sicher = katalog.zuordnen_heuristisch(z)
        if schluessel == "sonstiges":
            continue
        if any(p["katalog_typ"] == schluessel for p in positionen):
            continue
        positionen.append({"bezeichnung": z, "katalog_typ": schluessel, "sicher": sicher})
    return {"bank": "", "positionen": positionen, "quelle": "heuristik"}


# -------------------------------------------------------- Unterlage pruefen

def _dateiname(typ: katalog.Typ, nachname: str) -> str:
    basis = re.sub(r"[^a-z0-9]+", "-", typ.name.lower().replace("ae", "ae")).strip("-")
    name = re.sub(r"[^a-z0-9]+", "-", nachname.lower()).strip("-") or "kunde"
    return f"{basis}-{name}.pdf"


def unterlage_pruefen(pdf_bytes: bytes, katalog_typ: str, bezeichnung: str, nachname: str) -> dict:
    """Prueft ein hochgeladenes PDF gegen die Pruefregeln des Typs.

    Rueckgabe: {"passt": bool|None, "erkannter_typ", "fehler": [..], "dateiname", "zusammenfassung", "quelle"}
    passt=None bedeutet: keine KI verfuegbar, Berater muss manuell pruefen.
    """
    typ = katalog.typ(katalog_typ)
    text, seiten = pdf_text(pdf_bytes)
    fehler = []
    if seiten == 0:
        return {"passt": False, "erkannter_typ": katalog_typ,
                "fehler": ["Die Datei ist kein lesbares PDF. Bitte als PDF speichern und neu hochladen."],
                "dateiname": _dateiname(typ, nachname), "zusammenfassung": "", "quelle": "vorpruefung"}
    nur_bild = len(text.strip()) < 20
    if nur_bild and katalog_typ != "objektfotos":
        fehler.append("Das PDF enthaelt nur ein Bild ohne Text. Bitte das Original-PDF hochladen oder den Scanner in der App nutzen.")
    regel = PRUEFREGELN.get(katalog_typ, "Lesbar, vollstaendig, zum Kunden und Objekt passend.")
    ergebnis = _anfrage(
        SYSTEM_PRUEFUNG,
        [_pdf_block(pdf_bytes), {"type": "text", "text": (
            f"Geforderte Unterlage laut Bank: '{bezeichnung}' (Katalogtyp {katalog_typ}: {typ.name}).\n"
            f"Name des Kunden: {nachname}.\nPruefregeln: {regel}\n"
            f"Pruefe: Ist das die richtige Unterlage? Erfuellt sie die Regeln? Nenne jeden Mangel als eigenen Satz. "
            f"Vergib einen Dateinamen nach dem Muster '{_dateiname(typ, nachname)}', ergaenzt um Monat/Jahr, wenn sinnvoll.")}],
        SCHEMA_PRUEFUNG,
    )
    if ergebnis is None:
        return {"passt": None if not fehler else False, "erkannter_typ": katalog_typ, "fehler": fehler,
                "dateiname": _dateiname(typ, nachname),
                "zusammenfassung": "Keine KI-Pruefung verfuegbar, Berater prueft manuell.", "quelle": "manuell"}
    ergebnis["fehler"] = fehler + list(ergebnis.get("fehler") or [])
    ergebnis["passt"] = bool(ergebnis.get("passt")) and not fehler
    if not ergebnis.get("dateiname", "").lower().endswith(".pdf"):
        ergebnis["dateiname"] = _dateiname(typ, nachname)
    ergebnis["dateiname"] = re.sub(r"[^A-Za-z0-9._-]+", "-", ergebnis["dateiname"])
    ergebnis["quelle"] = "ki"
    return ergebnis
