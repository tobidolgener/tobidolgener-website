"""PDF-Erzeugung: Vollmacht des Verkaeufers (Vorlage), Beschaffungsauftrag mit Vollmacht
fuer den Berater (in der App unterschrieben), Export-Paket fuer Europace."""
import io
import json
import zipfile
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import katalog
from db import jetzt


def _umbruch(c, text: str, x: float, y: float, breite: float, zeilenhoehe: float = 14, schrift=("Helvetica", 10.5)) -> float:
    """Einfacher Zeilenumbruch. Gibt die naechste freie y-Position zurueck."""
    c.setFont(*schrift)
    from reportlab.pdfbase.pdfmetrics import stringWidth
    for absatz in text.split("\n"):
        worte, zeile = absatz.split(" "), ""
        for w in worte:
            probe = (zeile + " " + w).strip()
            if stringWidth(probe, schrift[0], schrift[1]) > breite and zeile:
                c.drawString(x, y, zeile)
                y -= zeilenhoehe
                zeile = w
            else:
                zeile = probe
        c.drawString(x, y, zeile)
        y -= zeilenhoehe
    return y


def _kopf(c, titel: str) -> float:
    b, h = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, h - 25 * mm, titel)
    c.setFont("Helvetica", 9)
    c.drawRightString(b - 20 * mm, h - 25 * mm, f"Stand: {date.today().strftime('%d.%m.%Y')}")
    c.line(20 * mm, h - 28 * mm, b - 20 * mm, h - 28 * mm)
    return h - 40 * mm


def vollmacht_verkaeufer(vorgang, kunde, berater, verkaeufer, typen: list[str]) -> bytes:
    """Vorlage, die der Verkaeufer unterschreibt. Berater holt damit Auszuege bei den Aemtern."""
    puffer = io.BytesIO()
    c = canvas.Canvas(puffer, pagesize=A4)
    b, _ = A4
    x, breite = 20 * mm, b - 40 * mm
    y = _kopf(c, "Vollmacht zur Einsichtnahme und Anforderung von Unterlagen")
    name = (verkaeufer.name if verkaeufer and verkaeufer.name else "____________________________________")
    adresse = (verkaeufer.adresse if verkaeufer and verkaeufer.adresse else "____________________________________")
    objekt = vorgang.bezeichnung or "____________________________________"
    zwecke = "\n".join(f"- {katalog.typ(t).name}" for t in typen) or "- Grundbuchauszug\n- Flurkarte\n- Auszug aus dem Baulastenverzeichnis"
    text = (
        f"Vollmachtgeber (Eigentuemer / Verkaeufer):\n{name}\n{adresse}\n\n"
        f"Objekt:\n{objekt}\n\n"
        f"Hiermit bevollmaechtige ich\n\n{berater.name}\n{berater.email}\n\n"
        f"im Rahmen der Immobilienfinanzierung von {kunde.name}, fuer das oben genannte Objekt folgende "
        f"Unterlagen bei den zustaendigen Stellen (Grundbuchamt, Katasteramt, Bauaufsicht) einzusehen und "
        f"anzufordern:\n\n{zwecke}\n\n"
        f"Die Vollmacht gilt ausschliesslich fuer diesen Zweck und erlischt mit Abschluss der Finanzierung, "
        f"spaetestens sechs Monate nach Unterzeichnung. Ein berechtigtes Interesse besteht durch den "
        f"beabsichtigten Verkauf an den Finanzierungskunden.\n\n\n"
        f"____________________________________        ____________________________________\n"
        f"Ort, Datum                                                   Unterschrift Vollmachtgeber"
    )
    _umbruch(c, text, x, y, breite)
    c.setFont("Helvetica", 7.5)
    c.drawString(x, 15 * mm, f"Erstellt mit AKTE fuer Vorgang {vorgang.id}. Bitte unterschrieben als PDF in der App hochladen.")
    c.save()
    return puffer.getvalue()


def auftrag_und_vollmacht(vorgang, kunde, berater, unterlagen: list, betrag: float,
                          unterschrift_png: bytes | None, nur_vollmacht: bool = False) -> bytes:
    """Beschaffungsauftrag (kostenpflichtig) und Vollmacht an den Berater, vom Kunden in der App unterschrieben."""
    puffer = io.BytesIO()
    c = canvas.Canvas(puffer, pagesize=A4)
    b, _ = A4
    x, breite = 20 * mm, b - 40 * mm
    titel = "Vollmacht fuer den Finanzierungsberater" if nur_vollmacht else "Beschaffungsauftrag und Vollmacht"
    y = _kopf(c, titel)
    positionen = "\n".join(
        f"- {u.bezeichnung}" + (f" ({u.preis_beschaffung:.2f} EUR)" if u.preis_beschaffung else "")
        for u in unterlagen
    )
    teile = [
        f"Auftraggeber:\n{kunde.name}\n{kunde.adresse or ''}\n{kunde.email}\n\n"
        f"Auftragnehmer / Bevollmaechtigter:\n{berater.name}\n{berater.email}\n\n"
        f"Finanzierungsvorgang: {vorgang.bezeichnung or vorgang.id}" + (f", Bank: {vorgang.bank}" if vorgang.bank else "") + "\n\n"
    ]
    if not nur_vollmacht:
        teile.append(
            f"1. Auftrag\nIch beauftrage den Auftragnehmer, folgende Unterlagen fuer meine Finanzierung zu beschaffen:\n\n"
            f"{positionen}\n\nVerguetung gesamt: {betrag:.2f} EUR (inkl. gesetzlicher Umsatzsteuer, sofern anfallend). "
            f"Auslagen der Aemter (Gebuehren fuer Auszuege) werden zusaetzlich nach Beleg erstattet.\n\n"
        )
    teile.append(
        f"{'2' if not nur_vollmacht else '1'}. Vollmacht\nIch bevollmaechtige den Auftragnehmer, in meinem Namen Unterlagen fuer "
        f"diese Finanzierung bei Dritten (Makler, Notar, Verkaeufer, Behoerden, Dienstleister) anzufordern, "
        f"entgegenzunehmen und in die Unterlagen-App sowie an die finanzierende Bank hochzuladen. "
        f"Die Vollmacht gilt bis zum Abschluss der Finanzierung, laengstens 12 Monate.\n\n"
        f"{'3' if not nur_vollmacht else '2'}. Hinweis\nDie Zinskondition der Bank ist befristet. Der Auftragnehmer uebernimmt keine Gewaehr "
        f"fuer Bearbeitungszeiten von Behoerden und Dritten.\n\n"
    )
    y = _umbruch(c, "".join(teile), x, y, breite)
    y -= 6 * mm
    if unterschrift_png:
        try:
            c.drawImage(ImageReader(io.BytesIO(unterschrift_png)), x, y - 22 * mm, width=60 * mm, height=22 * mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:  # noqa: BLE001
            pass
    y -= 24 * mm
    c.line(x, y, x + 70 * mm, y)
    c.setFont("Helvetica", 9)
    c.drawString(x, y - 4 * mm, f"{kunde.name}, elektronisch unterschrieben am {jetzt().strftime('%d.%m.%Y %H:%M')}")
    c.setFont("Helvetica", 7.5)
    c.drawString(x, 15 * mm, f"Erstellt mit AKTE fuer Vorgang {vorgang.id}. Unterschrift in der App erfasst.")
    c.save()
    return puffer.getvalue()


def export_paket(vorgang, kunde, dateien: list[tuple[str, bytes]], vollmachten: list[tuple[str, bytes]]) -> bytes:
    """ZIP fuer Europace: nummerierte, sprechende Dateinamen plus Inhaltsverzeichnis und Freigabenachweis."""
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
        inhalt = [f"Unterlagen {kunde.name} - Vorgang {vorgang.id} - {vorgang.bezeichnung}", ""]
        for i, (name, daten) in enumerate(dateien, 1):
            dateiname = f"{i:02d}_{name}"
            z.writestr(dateiname, daten)
            inhalt.append(dateiname)
        for name, daten in vollmachten:
            z.writestr(f"vollmacht/{name}", daten)
            inhalt.append(f"vollmacht/{name}")
        freigabe = (
            f"Freigabe durch Kunde in der App: {vorgang.freigabe_kunde_am or '-'}\n"
            f"Schriftliche Bestaetigung liegt dem Berater vor: {'ja' if vorgang.freigabe_schriftlich else 'nein'}\n"
            f"Export am: {jetzt()}\n"
        )
        z.writestr("00_inhalt.txt", "\n".join(inhalt) + "\n\n" + freigabe)
    return puffer.getvalue()
