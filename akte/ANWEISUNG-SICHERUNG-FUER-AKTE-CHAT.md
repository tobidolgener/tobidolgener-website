# Anweisung an den lokalen AKTE-Chat: Sicherung einbauen und in Betrieb nehmen

**Von:** Cloud-Session „Baufinanzierung-Berater WebApp" · **Stand:** 12.10.2026
**Zu:** `BAUAUFTRAG-AKTE-SICHERUNG-2026-10-12.md` und `ZULIEFERUNG-AKTE-SICHERUNG-2026-10-12.md` vom Architekt-Chat

Die Sicherung ist gebaut, getestet und auf GitHub (Branch `claude/baufinanzierung-berater-webapp-zhabad`,
Commits ab `8d88aaa`). Ich komme nicht an deinen Klon und nicht an den Server. Du hast beides.
Dein Klon hat vier lokale Commits (Face ID, `98e9d64`…`c68bb95`) und laut Architekt am 08.10. halbfertige
Aenderungen in `einstellungen.py` und `auth.py`. Die bleiben unberuehrt; die Sicherung liegt in eigenen Dateien.

## 1 · Holen und zusammenfuehren (im Klon `~/Desktop/Claude/akte-repo`)
```
git status                      # halbfertiges erst committen oder stashen, nichts verwerfen
git fetch origin claude/baufinanzierung-berater-webapp-zhabad
git merge origin/claude/baufinanzierung-berater-webapp-zhabad
```
Neue Dateien: `backend/sicherung.py`, `backend/pruefung/gegenprobe.py`, `deploy/akte-sicherung@.service`,
`deploy/akte-sicherung-taeglich.timer`, `deploy/akte-sicherung-probe.timer`.
Geaenderte Dateien: `backend/selftest.py` (sechs Gates am Ende angehaengt, drei Importe oben), `ausrollen.sh`
(Units kopieren und aktivieren, Gegenprobe in Schritt 1b, Nachtrag der Sicherungsvariablen in Schritt 4),
`deploy/einrichten.sh`, `UEBERGABE.md`, Design-Dateien unter `static/`.
Konflikte sind nur in `selftest.py` und `ausrollen.sh` zu erwarten; beide Seiten behalten.

## 2 · Pflichttabellen
`sicherung.PFLICHT_WUNSCH` enthaelt `faceid` und `faceid_kunde`. Pflicht werden sie automatisch, sobald die
Tabellen in `db.Basis.metadata` stehen (bei dir: ja). Pruefe nach dem Merge:
`cd backend && .venv/bin/python -c "import sicherung; print(sicherung.pflichttabellen())"`
Erwartet: alle neun aus dem Bauauftrag.

## 3 · Gates und Gegenprobe lokal
```
cd backend && .venv/bin/pip install -q -r ../requirements.txt
.venv/bin/python selftest.py              # ALLE GRUEN
.venv/bin/python pruefung/gegenprobe.py   # ALLE GATES GREIFEN (sieben Rueckbauten)
```

## 4 · Ausrollen
`./ausrollen.sh` aus `akte/`. Schritt 1b fuehrt die Gegenprobe aus, Schritt 3 kopiert die drei neuen Units und
aktiviert die Timer, Schritt 4 traegt in `/etc/akte.env` nach, falls sie fehlen:
`AKTE_SICHERUNG_KEY` (neu erzeugt, NICHT `AKTE_GEHEIMNIS`), `AKTE_STORAGEBOX_ZIEL`, `AKTE_STORAGEBOX_PFAD=akte-backups`,
`STORAGEBOX_KEY=/root/.ssh/storagebox`.
**Danach `AKTE_SICHERUNG_KEY` aus `/etc/akte.env` in den Passwort-Manager des CEO.** Ohne ihn sind alle Sicherungen wertlos.

## 5 · Erste Sicherung und erste Rueckholprobe von Hand (als root auf dem Server)
```
systemctl start akte-sicherung@taeglich.service && journalctl -u akte-sicherung@taeglich -n 5 --no-pager
systemctl start akte-sicherung@rueckholprobe.service && journalctl -u akte-sicherung@rueckholprobe -n 8 --no-pager
systemctl list-timers 'akte-*'
```
Erwartet: `OK   taeglich: akte-YYYYMMDD-HHMMSS.sich: N Zeilen in M Tabellen, K Dateien, ...` und
`OK   rueckholprobe: ... K Dateien verifiziert, 9 Pflichttabellen, alles stimmt`. Der Berater bekommt den Push
„Rueckholprobe der AKTE-Sicherung: in Ordnung."
Faellt die Probe rot aus, steht der Grund in der Zeile. Nichts auf der Box loeschen.
Falls `akte-backups` auf der Box fehlt: `sicherung.py` legt den Ordner beim ersten `ls` an (`mkdir -p`), sonst
von Hand: `ssh -p23 -i /root/.ssh/storagebox u653836@u653836.your-storagebox.de mkdir akte-backups`.

## 6 · Dem Architekt-Chat melden
Wenn `akte-sicherung-taeglich.timer` laeuft und die erste Rueckholprobe gruen ist, dem Architekt-Chat melden,
damit er in `/opt/wache/wache.py` nachtraegt: `"akte-backups": 30` und die beiden Timer. `/opt/wache/` nicht anfassen.

## 7 · Push nach GitHub
Der Architekt pusht nach Hausregel nicht. Ob dein Stand (Face ID, Zugangscodes) nach GitHub geht, entscheidet der CEO.
Solange er nicht gepusht ist, baut die Cloud-Session auf einem aelteren Stand; Konflikte werden mit jedem Auftrag groesser.
