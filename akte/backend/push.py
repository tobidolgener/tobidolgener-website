"""Web Push (VAPID) fuer Kunden und Berater. Rueckfall auf Mail, wenn kein Abo da ist."""
import base64
import json
import sys

import einstellungen as E
from db import PushAbo, logbuch, select

try:
    from pywebpush import webpush, WebPushException
except ImportError:  # pragma: no cover
    webpush = None
    WebPushException = Exception

# Im Selbsttest wird hier eine Attrappe eingehaengt
_sender = None


def verfuegbar() -> bool:
    return bool(E.VAPID_PRIVAT and E.VAPID_OEFFENTLICH and webpush)


def abo_speichern(s, inhaber_art: str, inhaber_id: int, abo: dict) -> PushAbo:
    endpoint = abo.get("endpoint", "")
    keys = abo.get("keys", {})
    vorhanden = s.scalar(select(PushAbo).where(PushAbo.endpoint == endpoint))
    if vorhanden:
        vorhanden.inhaber_art, vorhanden.inhaber_id = inhaber_art, inhaber_id
        vorhanden.p256dh, vorhanden.auth = keys.get("p256dh", ""), keys.get("auth", "")
        vorhanden.fehler = 0
        return vorhanden
    neu = PushAbo(inhaber_art=inhaber_art, inhaber_id=inhaber_id, endpoint=endpoint,
                  p256dh=keys.get("p256dh", ""), auth=keys.get("auth", ""))
    s.add(neu)
    return neu


def hat_abo(s, inhaber_art: str, inhaber_id: int) -> bool:
    return s.scalar(select(PushAbo).where(PushAbo.inhaber_art == inhaber_art,
                                          PushAbo.inhaber_id == inhaber_id)) is not None


def senden(s, inhaber_art: str, inhaber_id: int, titel: str, text: str, url: str = "/") -> int:
    """Schickt an alle Abos des Inhabers. Rueckgabe: Anzahl erfolgreicher Zustellungen."""
    abos = s.scalars(select(PushAbo).where(PushAbo.inhaber_art == inhaber_art,
                                           PushAbo.inhaber_id == inhaber_id)).all()
    nutzlast = json.dumps({"titel": titel, "text": text, "url": url})
    erfolg = 0
    for abo in abos:
        try:
            if _sender is not None:
                _sender(abo, nutzlast)
            elif verfuegbar():
                webpush(
                    subscription_info={"endpoint": abo.endpoint, "keys": {"p256dh": abo.p256dh, "auth": abo.auth}},
                    data=nutzlast,
                    vapid_private_key=E.VAPID_PRIVAT,
                    vapid_claims={"sub": E.VAPID_KONTAKT},
                    ttl=86400,
                )
            else:
                continue
            erfolg += 1
        except WebPushException as ex:  # Abo tot (410/404) -> loeschen
            status = getattr(getattr(ex, "response", None), "status_code", None)
            if status in (404, 410):
                s.delete(abo)
            else:
                abo.fehler += 1
        except Exception:  # noqa: BLE001
            abo.fehler += 1
    logbuch(s, "push", f"{inhaber_art} {inhaber_id}: {titel} ({erfolg}/{len(abos)} zugestellt)")
    return erfolg


def schluessel_erzeugen() -> tuple[str, str]:
    """VAPID-Schluesselpaar: (privat, oeffentlich) base64url."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    privat = ec.generate_private_key(ec.SECP256R1())
    roh = privat.private_numbers().private_value.to_bytes(32, "big")
    oeff = privat.public_key().public_bytes(serialization.Encoding.X962,
                                           serialization.PublicFormat.UncompressedPoint)
    b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")  # noqa: E731
    return b64(roh), b64(oeff)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "schluessel":
        p, o = schluessel_erzeugen()
        print(f"AKTE_VAPID_PRIVAT={p}\nAKTE_VAPID_OEFFENTLICH={o}")
    else:
        print("Aufruf: python push.py schluessel")
