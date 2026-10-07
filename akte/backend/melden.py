"""Benachrichtigungen: Push zuerst, Mail als Rueckfall. Alles landet im Logbuch."""
import einstellungen as E
import post
import push
from db import logbuch


def kunde_melden(s, kunde, titel: str, text: str, pfad: str = "/app") -> str:
    url = E.BASIS_URL + pfad
    if push.senden(s, "kunde", kunde.id, titel, text, pfad) > 0:
        weg = "push"
    else:
        betreff, body = post.text_kunde_hinweis(kunde, titel, text, url)
        post.senden(s, kunde.email, betreff, body)
        weg = "mail"
    logbuch(s, "meldung_kunde", f"{titel} ({weg})", kunde_id=kunde.id)
    return weg


def berater_melden(s, berater, titel: str, text: str, pfad: str = "/berater", vorgang_id=None) -> str:
    url = E.BASIS_URL + pfad
    weg = "push" if push.senden(s, "berater", berater.id, titel, text, pfad) > 0 else ""
    if berater.email:
        betreff, body = post.text_berater_hinweis(berater, titel, text, url)
        post.senden(s, berater.email, betreff, body)
        weg = (weg + "+mail") if weg else "mail"
    logbuch(s, "meldung_berater", f"{titel} ({weg or 'kein weg'})", berater_id=berater.id, vorgang_id=vorgang_id)
    return weg
