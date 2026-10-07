#!/usr/bin/env bash
# Einmalige Einrichtung auf dem Server (laeuft als root, wird von ausrollen.sh gestartet, wenn /etc/akte.env fehlt).
# Legt an: Systempakete, Postgres-Datenbank, /etc/akte.env mit Geheimnissen und VAPID-Schluesseln, Caddy-Block.
# Vorgaben kommen als Umgebungsvariablen (ANTHROPIC_API_KEY, AKTE_SMTP_*, AKTE_BERATER_EMAIL, AKTE_BERATER_PASSWORT).
set -euo pipefail
ZIEL="${ZIEL:-/opt/akte}"
DOMAIN="${AKTE_DOMAIN:-akte.reika.live}"
ENV=/etc/akte.env

echo "-- Systempakete"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq python3-venv python3-pip rsync ocrmypdf tesseract-ocr-deu >/dev/null 2>&1 || \
  echo "   Hinweis: apt-Pakete konnten nicht alle installiert werden (ocrmypdf ist optional)."

echo "-- Datenbank"
DBPASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
if command -v psql >/dev/null && id postgres >/dev/null 2>&1; then
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='akte'" | grep -q 1 || \
    sudo -u postgres psql -qc "CREATE ROLE akte LOGIN PASSWORD '$DBPASS';"
  sudo -u postgres psql -qc "ALTER ROLE akte PASSWORD '$DBPASS';"
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='akte'" | grep -q 1 || \
    sudo -u postgres psql -qc "CREATE DATABASE akte OWNER akte;"
  DATABASE_URL="postgresql+psycopg2://akte:$DBPASS@127.0.0.1:5432/akte"
  echo "   Postgres-Datenbank 'akte' bereit"
else
  DATABASE_URL="sqlite:///$ZIEL/daten/akte.db"
  echo "   Kein Postgres gefunden, nehme SQLite unter $ZIEL/daten/akte.db"
fi

echo "-- Geheimnisse"
GEHEIMNIS=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
BUCHUNG=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
BERATER_PW="${AKTE_BERATER_PASSWORT:-$(python3 -c "import secrets; print(secrets.token_urlsafe(10))")}"
VAPID=$(cd "$ZIEL/backend" && .venv/bin/python push.py schluessel)

cat > "$ENV" <<ENVEOF
# AKTE - angelegt von einrichten.sh am $(date -Is). Werte mit ERSETZEN bitte ausfuellen, dann: systemctl restart akte
AKTE_PORT=${AKTE_PORT:-8410}
AKTE_BASIS_URL=https://$DOMAIN
AKTE_GEHEIMNIS=$GEHEIMNIS
AKTE_DATEN=$ZIEL/daten
DATABASE_URL=$DATABASE_URL

AKTE_BERATER_NAME=${AKTE_BERATER_NAME:-Tobi Dolgener}
AKTE_BERATER_EMAIL=${AKTE_BERATER_EMAIL:-tobias@pathfinders.berlin}
AKTE_BERATER_PASSWORT=$BERATER_PW

AKTE_SMTP_HOST=${AKTE_SMTP_HOST:-}
AKTE_SMTP_PORT=${AKTE_SMTP_PORT:-587}
AKTE_SMTP_USER=${AKTE_SMTP_USER:-}
AKTE_SMTP_PASSWORT=${AKTE_SMTP_PASSWORT:-}
AKTE_ABSENDER=${AKTE_ABSENDER:-${AKTE_SMTP_USER:-}}

$VAPID
AKTE_VAPID_KONTAKT=mailto:${AKTE_BERATER_EMAIL:-tobias@pathfinders.berlin}

ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
AKTE_KI_MODELL=${AKTE_KI_MODELL:-claude-opus-5-5}

AKTE_BUCHUNG_SCHLUESSEL=$BUCHUNG

AKTE_SCAN_MIN_SCHAERFE=60
AKTE_SCAN_MIN_HELLIGKEIT=70
AKTE_SCAN_MAX_HELLIGKEIT=235
AKTE_NACHFRAGE_MAKLER_TAGE=2
ENVEOF
chmod 600 "$ENV"
echo "   $ENV geschrieben"

echo "-- Caddy"
CADDYFILE=""
for k in /etc/caddy/Caddyfile /etc/caddy/conf.d/reika.caddy; do [ -f "$k" ] && CADDYFILE="$k" && break; done
if [ -n "$CADDYFILE" ]; then
  if grep -q "$DOMAIN" "$CADDYFILE"; then
    echo "   $DOMAIN steht schon in $CADDYFILE"
  else
    cat >> "$CADDYFILE" <<CADDYEOF

$DOMAIN {
    encode zstd gzip
    request_body {
        max_size 30MB
    }
    reverse_proxy 127.0.0.1:${AKTE_PORT:-8410}
}
CADDYEOF
    (caddy validate --config "$CADDYFILE" >/dev/null 2>&1 && systemctl reload caddy && echo "   Caddy-Block fuer $DOMAIN angehaengt und Caddy neu geladen") || \
      echo "   ACHTUNG: Caddy-Block angehaengt, aber Validierung/Reload fehlgeschlagen. Bitte $CADDYFILE pruefen."
  fi
else
  echo "   ACHTUNG: Keine Caddy-Konfiguration gefunden. Block aus $ZIEL/Caddyfile.akte von Hand einhaengen."
fi

echo
echo "=============================================================="
echo " Berater-Login:  ${AKTE_BERATER_EMAIL:-tobias@pathfinders.berlin}"
echo " Startpasswort:  $BERATER_PW   (in den Einstellungen aendern)"
echo " Buchungsschluessel fuer /api/buchung: $BUCHUNG"
[ -z "${ANTHROPIC_API_KEY:-}" ] && echo " KI: AUS (ANTHROPIC_API_KEY fehlt in $ENV)"
[ -z "${AKTE_SMTP_HOST:-}" ] && echo " Mail: nur Ablage unter $ZIEL/daten/ausgang (AKTE_SMTP_* fehlt in $ENV)"
echo "=============================================================="
