#!/usr/bin/env bash
# Rollt AKTE auf reika-portal aus. Bricht ab, wenn der Selbsttest rot ist.
# Ablauf: 1/5 Selbsttest lokal  2/5 Code uebertragen  3/5 venv + Abhaengigkeiten (+ erste Einrichtung)
#         4/5 Dienst neu starten 5/5 Beweis am laufenden Dienst (/version-Abdruck)
# Erster Lauf: ANTHROPIC_API_KEY=... AKTE_SMTP_HOST=... AKTE_SMTP_USER=... AKTE_SMTP_PASSWORT=... ./ausrollen.sh
set -euo pipefail
HIER="$(cd "$(dirname "$0")" && pwd)"
SERVER="${AKTE_SERVER:-root@46.224.96.148}"
SSH_KEY="${AKTE_SSH_KEY:-$HOME/.ssh/reika-portal-hetzner}"
ZIEL="/opt/akte"
URL="${AKTE_URL:-https://akte.reika.live}"
SSH="ssh -i $SSH_KEY -o ConnectTimeout=25 $SERVER"
PY="${AKTE_PYTHON:-python3}"

echo "== 1/5 Selbsttest lokal =="
if [ -x "$HIER/backend/.venv/bin/python" ]; then PY="$HIER/backend/.venv/bin/python"; fi
( cd "$HIER/backend" && "$PY" selftest.py ) || { echo "ABBRUCH: Selbsttest rot"; exit 1; }
ABDRUCK_LOKAL=$( cd "$HIER/backend" && "$PY" -c "import main; print(main.ABDRUCK)" )
COMMIT=$(git -C "$HIER" rev-parse --short HEAD 2>/dev/null || echo "ohne-git")

echo "== 2/5 Code uebertragen ($COMMIT, Abdruck $ABDRUCK_LOKAL) =="
$SSH "command -v rsync >/dev/null && python3 -c 'import venv' 2>/dev/null || (apt-get update -qq && apt-get install -y -qq rsync python3-venv >/dev/null); \
      id akte >/dev/null 2>&1 || useradd -r -m -d $ZIEL -s /usr/sbin/nologin akte; mkdir -p $ZIEL/daten"
rsync -az --delete -e "ssh -i $SSH_KEY" \
  --exclude '.venv' --exclude '__pycache__' --exclude 'daten' --exclude '*.db' \
  "$HIER/backend/" "$SERVER:$ZIEL/backend/"
rsync -az -e "ssh -i $SSH_KEY" "$HIER/requirements.txt" "$HIER/deploy/" "$SERVER:$ZIEL/"

echo "== 3/5 venv und Abhaengigkeiten =="
$SSH "cd $ZIEL/backend && [ -d .venv ] || python3 -m venv .venv; \
      .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r $ZIEL/requirements.txt; \
      cp $ZIEL/akte.service $ZIEL/akte-zeitplan.service $ZIEL/akte-zeitplan.timer /etc/systemd/system/; \
      chown -R akte:akte $ZIEL; systemctl daemon-reload; systemctl enable -q akte akte-zeitplan.timer"

if ! $SSH "test -f /etc/akte.env"; then
  echo "== 3a/5 Erste Einrichtung auf dem Server (Datenbank, Geheimnisse, Push-Schluessel, Caddy) =="
  $SSH "cd $ZIEL && chmod +x einrichten.sh && ZIEL=$ZIEL AKTE_DOMAIN=${AKTE_DOMAIN:-akte.reika.live} \
        ANTHROPIC_API_KEY='${ANTHROPIC_API_KEY:-}' AKTE_SMTP_HOST='${AKTE_SMTP_HOST:-}' AKTE_SMTP_PORT='${AKTE_SMTP_PORT:-587}' \
        AKTE_SMTP_USER='${AKTE_SMTP_USER:-}' AKTE_SMTP_PASSWORT='${AKTE_SMTP_PASSWORT:-}' AKTE_ABSENDER='${AKTE_ABSENDER:-}' \
        AKTE_BERATER_EMAIL='${AKTE_BERATER_EMAIL:-}' AKTE_BERATER_NAME='${AKTE_BERATER_NAME:-}' AKTE_BERATER_PASSWORT='${AKTE_BERATER_PASSWORT:-}' \
        ./einrichten.sh"
fi

echo "== 3b/5 Selbsttest auf dem Server =="
$SSH "cd $ZIEL/backend && sudo -u akte env AKTE_DATEN=/tmp/akte-selftest .venv/bin/python selftest.py | tail -3" || { echo "ABBRUCH: Selbsttest auf dem Server rot"; exit 1; }

echo "== 4/5 Dienst neu starten =="
$SSH "systemctl restart akte && systemctl start akte-zeitplan.timer && sleep 2 && systemctl is-active akte && echo 'Zeitplan: '\$(systemctl is-enabled akte-zeitplan.timer)"

echo "== 5/5 Beweis am laufenden Dienst (nicht am Build-Log) =="
GELIEFERT=$(curl -s --max-time 15 "$URL/version" | "$PY" -c "import sys,json; print(json.load(sys.stdin)['abdruck'])" 2>/dev/null || echo "keine-antwort")
echo "erwartet:  $ABDRUCK_LOKAL"
echo "geliefert: $GELIEFERT"
if [ "$GELIEFERT" = "$ABDRUCK_LOKAL" ]; then
  echo "OK -- AKTE laeuft mit Abdruck $GELIEFERT (Commit $COMMIT)"
else
  echo "FEHLER -- der laufende Dienst liefert nicht den erwarteten Abdruck"; exit 1
fi
