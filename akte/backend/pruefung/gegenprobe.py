"""Gegenprobe: baut die Sicherung gezielt kaputt und verlangt, dass das zugehoerige Gate ROT wird.

Ein Gate, das bei kaputtem Code gruen bleibt, misst nichts. Aufruf aus backend/:
    python pruefung/gegenprobe.py            alle Rueckbauten
    AKTE_NUR=klartext python pruefung/gegenprobe.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent

# (gate, datei, original, rueckbau, begruendung)
RUECKBAUTEN = [
    ("was-die-box-verlaesst-ist-nie-klartext", "sicherung.py",
     "return MAGIE + nonce + AESGCM(key).encrypt(nonce, daten, MAGIE)",
     "return MAGIE + nonce + daten  # RUECKBAU: Klartext",
     "ohne Verschluesselung muss das Gate Klartext im Paket finden"),
    ("was-die-box-verlaesst-ist-nie-klartext", "sicherung.py",
     "        return AESGCM(key).decrypt(nonce, rest, MAGIE)",
     "        return AESGCM(key).decrypt(nonce, rest, MAGIE) if len(rest) % 2 else rest  # RUECKBAU",
     "ein stilles Entpacken statt Ablehnung muss auffallen (Platzhalter: Bitkipp wird nicht mehr sicher abgelehnt)"),
    ("die-rueckholprobe-merkt-eine-leere-sicherung", "sicherung.py",
     "            if erwartet and geprueft == 0:",
     "            if False:  # RUECKBAU: leere Sicherung ignorieren",
     "die Probe darf eine Sicherung ohne Dateien nicht durchwinken"),
    ("die-rueckholprobe-merkt-eine-leere-sicherung", "sicherung.py",
     "                if meta.get(\"groesse\", 0) <= 0:",
     "                if False:  # RUECKBAU: Nullbyte-Dateien ignorieren",
     "eine Datei mit 0 Bytes muss rot sein"),
    ("die-rueckholprobe-merkt-eine-leere-sicherung", "sicherung.py",
     "                elif gezaehlt.get(t, 0) != kopf[\"zeilen\"][t]:",
     "                elif False:  # RUECKBAU: Zeilen nicht nachzaehlen",
     "die Probe muss die Zeilen im Dump gegen den Kopf halten"),
    ("eine-alte-sicherung-gilt-nicht-als-frische", "sicherung.py",
     "        if alter > timedelta(hours=HOECHSTALTER_STUNDEN):",
     "        if False:  # RUECKBAU: Alter ignorieren",
     "eine zu alte Sicherung muss rot sein"),
]


def lauf(nur: str | None = None) -> int:
    rot = 0
    for gate, datei, original, rueckbau, grund in RUECKBAUTEN:
        if nur and nur not in gate and nur not in grund:
            continue
        with tempfile.TemporaryDirectory(prefix="akte-gegenprobe-") as d:
            kopie = Path(d) / "backend"
            shutil.copytree(HIER, kopie, ignore=shutil.ignore_patterns("daten", "__pycache__", ".venv", "*.db"))
            quelle = kopie / datei
            text = quelle.read_text()
            if original not in text:
                print(f"ROT    {gate}: Original-Schnipsel nicht gefunden in {datei} ({grund})")
                rot += 1
                continue
            quelle.write_text(text.replace(original, rueckbau, 1))
            umgebung = dict(os.environ, AKTE_NUR=gate, AKTE_DATEN=tempfile.mkdtemp(prefix="akte-gp-"))
            erg = subprocess.run([sys.executable, "selftest.py"], cwd=kopie, env=umgebung, capture_output=True, text=True, timeout=600)
            if f"ROT    {gate}" in erg.stdout:
                print(f"GRUEN  {gate} wird rot bei Rueckbau: {grund}")
            else:
                print(f"ROT    {gate} bleibt gruen bei Rueckbau: {grund}")
                print(erg.stdout[-800:])
                rot += 1
    print(f"\nGEGENPROBE: {'ALLE GATES GREIFEN' if not rot else str(rot) + ' GATE(S) MESSEN NICHTS'}")
    return 1 if rot else 0


if __name__ == "__main__":
    sys.exit(lauf(os.environ.get("AKTE_NUR")))
