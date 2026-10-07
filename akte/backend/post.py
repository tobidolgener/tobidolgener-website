"""Mailversand. SMTP wenn konfiguriert, sonst Ablage als .eml im Ausgangsordner.
Jede Mail landet im Protokoll (Tabelle ausgang)."""
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

import einstellungen as E
from db import Ausgang, jetzt


def senden(s, an: str, betreff: str, text: str) -> Ausgang:
    eintrag = Ausgang(an=an, betreff=betreff, text=text)
    msg = EmailMessage()
    msg["From"] = E.ABSENDER or E.SMTP_USER or "akte@localhost"
    msg["To"] = an
    msg["Subject"] = betreff
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(text)
    try:
        if E.SMTP_HOST:
            with smtplib.SMTP(E.SMTP_HOST, E.SMTP_PORT, timeout=20) as smtp:
                smtp.starttls()
                if E.SMTP_USER:
                    smtp.login(E.SMTP_USER, E.SMTP_PASSWORT)
                smtp.send_message(msg)
            eintrag.weg = "smtp"
        else:
            E.AUSGANG_ORDNER.mkdir(parents=True, exist_ok=True)
            name = jetzt().strftime("%Y%m%d-%H%M%S") + "-" + "".join(c for c in an if c.isalnum())[:30] + ".eml"
            (E.AUSGANG_ORDNER / name).write_bytes(bytes(msg))
            eintrag.weg = "ordner"
    except Exception as ex:  # noqa: BLE001 - Fehler protokollieren, nicht abbrechen
        eintrag.fehler = str(ex)[:1000]
        eintrag.weg = "fehler"
    s.add(eintrag)
    return eintrag


# ------------------------------------------------------------- Mailtexte

def text_einstieg(kunde, berater, link: str) -> tuple[str, str]:
    betreff = f"Dein Zugang zur Unterlagen-App von {berater.name}"
    text = (
        f"Hallo {kunde.vorname},\n\n"
        f"dein Berater {berater.name} freut sich auf den Termin mit dir.\n\n"
        f"Zur Vorbereitung braucht er deine letzten drei Nettogehaelter. "
        f"Bitte klicke auf diesen Link und trage sie ein, das dauert eine Minute:\n\n"
        f"{link}\n\n"
        f"Wir lesen nur dein Nettogehalt aus und speichern keine Nachweise.\n\n"
        f"Der Link ist 30 Tage gueltig und nur fuer dich bestimmt.\n\n"
        f"Viele Gruesse\n{berater.name}\n"
    )
    return betreff, text


def text_anmeldelink(kunde, link: str) -> tuple[str, str]:
    return ("Dein Anmeldelink",
            f"Hallo {kunde.vorname},\n\nhier ist dein Link zum Anmelden:\n\n{link}\n\n"
            f"Der Link ist 30 Tage gueltig. Wenn du ihn nicht angefordert hast, ignoriere diese Mail.\n")


def text_berater_hinweis(berater, titel: str, text: str, link: str) -> tuple[str, str]:
    return (f"AKTE: {titel}", f"Hallo {berater.name.split()[0]},\n\n{text}\n\n{link}\n")


def text_kunde_hinweis(kunde, titel: str, text: str, link: str) -> tuple[str, str]:
    return (titel, f"Hallo {kunde.vorname},\n\n{text}\n\nZur App: {link}\n")


def makler_mail_text(kunde, vorgang, unterlagen: list, makler_name: str, mahnung: bool = False) -> tuple[str, str]:
    """Text fuer den mailto-Link an den Makler. Kurz halten (mailto-Laengenbegrenzung)."""
    objekt = vorgang.bezeichnung or "die Immobilie"
    zeilen = "\n".join(f"- {u.bezeichnung}" for u in unterlagen)
    anrede = f"Guten Tag {makler_name}," if makler_name else "Guten Tag,"
    if mahnung:
        betreff = f"Erinnerung: Unterlagen fuer {objekt}"
        text = (f"{anrede}\n\nich hatte Sie bereits um folgende Unterlagen fuer {objekt} gebeten "
                f"und bitte dringend um Zusendung, da die Zinskondition meiner Finanzierung befristet ist:\n\n"
                f"{zeilen}\n\nVielen Dank und freundliche Gruesse\n{kunde.name}")
    else:
        betreff = f"Unterlagen fuer {objekt}"
        text = (f"{anrede}\n\nfuer die Finanzierung von {objekt} benoetigt meine Bank folgende Unterlagen. "
                f"Bitte senden Sie mir diese als PDF zu:\n\n{zeilen}\n\n"
                f"Vielen Dank und freundliche Gruesse\n{kunde.name}")
    return betreff, text
