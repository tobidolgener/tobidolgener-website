"""Anmeldung: Passwort fuer Berater, Anmeldelink fuer Kunden, signierte Sitzungs-Cookies."""
import hashlib
import hmac
import secrets

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

import einstellungen as E

COOKIE = "akte_sitzung"
SITZUNG_TAGE_KUNDE = 90
SITZUNG_TAGE_BERATER = 30

_serializer = URLSafeTimedSerializer(E.GEHEIMNIS, salt="akte-sitzung")


def passwort_hash(passwort: str) -> str:
    salz = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", passwort.encode(), salz.encode(), 200_000).hex()
    return f"pbkdf2${salz}${h}"


def passwort_pruefen(passwort: str, gespeichert: str) -> bool:
    try:
        _, salz, h = gespeichert.split("$")
    except ValueError:
        return False
    neu = hashlib.pbkdf2_hmac("sha256", passwort.encode(), salz.encode(), 200_000).hex()
    return hmac.compare_digest(neu, h)


def sitzung_token(art: str, inhaber_id: int) -> str:
    return _serializer.dumps({"art": art, "id": inhaber_id})


def sitzung_lesen(token: str | None) -> tuple[str, int] | None:
    if not token:
        return None
    try:
        daten = _serializer.loads(token, max_age=SITZUNG_TAGE_KUNDE * 86400)
    except (BadSignature, SignatureExpired):
        return None
    art, inhaber_id = daten.get("art"), daten.get("id")
    if art not in ("kunde", "berater") or not isinstance(inhaber_id, int):
        return None
    return art, inhaber_id


def cookie_setzen(response, art: str, inhaber_id: int, sicher: bool) -> None:
    tage = SITZUNG_TAGE_KUNDE if art == "kunde" else SITZUNG_TAGE_BERATER
    response.set_cookie(COOKIE, sitzung_token(art, inhaber_id), max_age=tage * 86400,
                        httponly=True, samesite="lax", secure=sicher, path="/")


def cookie_loeschen(response) -> None:
    response.delete_cookie(COOKIE, path="/")
