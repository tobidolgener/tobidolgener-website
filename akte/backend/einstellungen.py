"""Konfiguration aus der Umgebung (/etc/akte.env auf dem Server)."""
import os
from pathlib import Path

BASIS = Path(__file__).resolve().parent
DATEN = Path(os.environ.get("AKTE_DATEN", BASIS / "daten"))
DATEN.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATEN / 'akte.db'}")
GEHEIMNIS = os.environ.get("AKTE_GEHEIMNIS", "nur-fuer-entwicklung-aendern")
BASIS_URL = os.environ.get("AKTE_BASIS_URL", "http://127.0.0.1:8410").rstrip("/")
PORT = int(os.environ.get("AKTE_PORT", "8410"))

# Erster Berater (wird beim Start angelegt, falls die Tabelle leer ist)
BERATER_NAME = os.environ.get("AKTE_BERATER_NAME", "Tobi Dolgener")
BERATER_EMAIL = os.environ.get("AKTE_BERATER_EMAIL", "")
BERATER_PASSWORT = os.environ.get("AKTE_BERATER_PASSWORT", "")

# Homepage-Buchung (geteiltes Geheimnis fuer POST /api/buchung)
BUCHUNG_SCHLUESSEL = os.environ.get("AKTE_BUCHUNG_SCHLUESSEL", "")

# Mail
SMTP_HOST = os.environ.get("AKTE_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("AKTE_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("AKTE_SMTP_USER", "")
SMTP_PASSWORT = os.environ.get("AKTE_SMTP_PASSWORT", "")
ABSENDER = os.environ.get("AKTE_ABSENDER", "")
AUSGANG_ORDNER = Path(os.environ.get("AKTE_AUSGANG_ORDNER", DATEN / "ausgang"))

# Web Push (VAPID). Schluessel erzeugen: python push.py schluessel
VAPID_PRIVAT = os.environ.get("AKTE_VAPID_PRIVAT", "")
VAPID_OEFFENTLICH = os.environ.get("AKTE_VAPID_OEFFENTLICH", "")
VAPID_KONTAKT = os.environ.get("AKTE_VAPID_KONTAKT", "mailto:" + (BERATER_EMAIL or "info@example.org"))

# KI
KI_MODELL = os.environ.get("AKTE_KI_MODELL", "claude-opus-5-5")
KI_AKTIV = bool(os.environ.get("ANTHROPIC_API_KEY"))

# Scanner-Schwellen (mit echten Fotos nachjustieren)
SCAN_MIN_SCHAERFE = float(os.environ.get("AKTE_SCAN_MIN_SCHAERFE", "60"))
SCAN_MIN_HELLIGKEIT = float(os.environ.get("AKTE_SCAN_MIN_HELLIGKEIT", "70"))
SCAN_MAX_HELLIGKEIT = float(os.environ.get("AKTE_SCAN_MAX_HELLIGKEIT", "235"))

# Fristen
NACHFRAGE_MAKLER_TAGE = int(os.environ.get("AKTE_NACHFRAGE_MAKLER_TAGE", "2"))
ERINNERUNG_WOECHENTLICH_TAGE = 7
MAX_UPLOAD_MB = int(os.environ.get("AKTE_MAX_UPLOAD_MB", "25"))

VERSION = "0.1.0"
