"""Sicherung fuer AKTE: Datenbank + Dateibaum, verschluesselt auf die Hetzner Storage Box.

Aufruf (als root, systemd reicht /etc/akte.env durch):
    python sicherung.py taeglich        Paket bauen, hochladen, alte Staende entfernen
    python sicherung.py rueckholprobe   juengstes Paket holen, entschluesseln, gegen den Kopf pruefen
    python sicherung.py liste           was liegt auf der Box

Von Hand: set -a; . /etc/akte.env; set +a; cd /opt/akte/backend && .venv/bin/python sicherung.py taeglich

Paketaufbau: akte-YYYYMMDD-HHMMSS.sich = MAGIE + Nonce + AES-GCM(tar.gz). Im tar: kopf.json (Zeilen je Tabelle,
Dateien mit Groesse und SHA-256, Abzug des Dumps), datenbank.sql, dateien/... Ein veraendertes Paket wird abgelehnt.
Die Rueckholprobe zaehlt die Zeilen im Dump nach und prueft jede Datei nach Groesse und Hash. Eine leere Sicherung
(Dateien fehlen oder null Bytes) ist rot, eine alte Sicherung (> HOECHSTALTER_STUNDEN) ist rot.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import inspect, text

import einstellungen as E
import db

# Marke und Nonce-Laenge stehen EINMAL (MILLER-Befund 24.09.2026: von Hand abgezaehlte Positionen
# haben beim Umbenennen der Marke jede Rueckholung unmoeglich gemacht).
MAGIE = b"AKTE-SICH1"
NONCE_LAENGE = 12
MUSTER = re.compile(r"^akte-\d{8}-\d{6}\.sich$")
HOECHSTALTER_STUNDEN = 30
AUFBEWAHRUNG_TAGE = 30
DATEI_ORDNER = ("vorgang", "muster")
# Aus dem Bauauftrag vom 12.10.2026. Nur Tabellen, die das Datenmodell kennt, werden Pflicht; kommt eine Tabelle
# (z. B. faceid) ins Datenmodell, wird sie hier automatisch Pflicht.
PFLICHT_WUNSCH = ("berater", "kunde", "vorgang", "unterlage", "vollmacht", "ereignis", "faceid", "faceid_kunde", "ausgang")


class SicherungsFehler(Exception):
    pass


def pflichttabellen() -> list[str]:
    return [t for t in PFLICHT_WUNSCH if t in db.Basis.metadata.tables]


# ------------------------------------------------------------ Schluessel

def schluessel() -> bytes:
    roh = os.environ.get("AKTE_SICHERUNG_KEY", "")
    if not roh:
        raise SicherungsFehler("AKTE_SICHERUNG_KEY fehlt in der Umgebung")
    return hashlib.sha256(roh.encode()).digest()


def verschluesseln(daten: bytes, key: bytes) -> bytes:
    nonce = os.urandom(NONCE_LAENGE)
    return MAGIE + nonce + AESGCM(key).encrypt(nonce, daten, MAGIE)


def entschluesseln(paket: bytes, key: bytes) -> bytes:
    a = len(MAGIE)
    if not paket.startswith(MAGIE) or len(paket) < a + NONCE_LAENGE + 16:
        raise SicherungsFehler("Paket abgelehnt: kein AKTE-Sicherungspaket")
    nonce, rest = paket[a:a + NONCE_LAENGE], paket[a + NONCE_LAENGE:]
    try:
        return AESGCM(key).decrypt(nonce, rest, MAGIE)
    except Exception as ex:  # noqa: BLE001 - InvalidTag u. a.
        raise SicherungsFehler("Paket abgelehnt: Pruefsumme stimmt nicht (veraendert oder falscher Schluessel)") from ex


# ------------------------------------------------------------ Transport

class OrdnerBox:
    """Ablage in einem lokalen Ordner. Fuer Selbsttest und als Rueckfall ohne Storage Box."""
    def __init__(self, pfad: str):
        self.pfad = Path(pfad)
        self.pfad.mkdir(parents=True, exist_ok=True)

    def liste(self) -> list[tuple[str, float]]:
        return [(p.name, p.stat().st_mtime) for p in self.pfad.iterdir() if p.is_file()]

    def hochladen(self, quelle: Path, name: str) -> None:
        shutil.copyfile(quelle, self.pfad / name)

    def holen(self, name: str, ziel: Path) -> None:
        shutil.copyfile(self.pfad / name, ziel)

    def loeschen(self, name: str) -> None:
        (self.pfad / name).unlink(missing_ok=True)


def _befehl(args: list, zeit: int = 1800) -> subprocess.CompletedProcess:
    """Die einzige Stelle, die Befehle ausfuehrt. Der Selbsttest ersetzt sie."""
    return subprocess.run(args, capture_output=True, timeout=zeit)


class StorageBox:
    """Hetzner Storage Box per SSH, Port 23. Eingeschraenkte Shell: kein find, kein sort, keine Pipes,
    und `cat > datei` meldete Erfolg und schrieb nichts (MILLER, 22.09.2026). Deshalb rsync, und nach dem
    Hochladen wird nachgesehen, ob die Datei DORT liegt."""
    def __init__(self, ziel: str, pfad: str, key: str, port: int = 23):
        if not re.fullmatch(r"[\w.-]+@[\w.-]+", ziel or "") or not re.fullmatch(r"[\w-]+", pfad or ""):
            raise SicherungsFehler("Storage Box nicht eingerichtet (AKTE_STORAGEBOX_ZIEL / AKTE_STORAGEBOX_PFAD)")
        self.ziel, self.pfad, self.key, self.port = ziel, pfad, key, port
        self.ssh = ["ssh", f"-p{port}", "-i", key, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "ConnectTimeout=25"]

    def _lauf(self, args: list, fehler: str, zeit: int = 1800) -> subprocess.CompletedProcess:
        r = _befehl(args, zeit)
        if r.returncode != 0:
            raise SicherungsFehler(f"{fehler}: {r.stderr.decode(errors='replace')[:300]}")
        return r

    def liste(self) -> list[tuple[str, float]]:
        r = _befehl(self.ssh + [self.ziel, f"ls -1 {self.pfad}"], 120)
        if r.returncode != 0:
            if b"No such file" in r.stderr:
                _befehl(self.ssh + [self.ziel, f"mkdir -p {self.pfad}"], 60)
                return []
            raise SicherungsFehler("Liste der Storage Box nicht lesbar: " + r.stderr.decode(errors="replace")[:300])
        namen = [n for n in r.stdout.decode(errors="replace").split() if n]
        return [(n, (zeit_aus_name(n) or datetime.fromtimestamp(0)).timestamp()) for n in namen]

    def hochladen(self, quelle: Path, name: str) -> None:
        self._lauf(["rsync", "-a", "--chmod=F600", "-e", " ".join(self.ssh), str(quelle),
                    f"{self.ziel}:{self.pfad}/{name}"], "rsync zur Storage Box gescheitert")

    def holen(self, name: str, ziel: Path) -> None:
        self._lauf(["rsync", "-a", "-e", " ".join(self.ssh), f"{self.ziel}:{self.pfad}/{name}", str(ziel)],
                   "rsync von der Storage Box gescheitert")

    def loeschen(self, name: str) -> None:
        self._lauf(self.ssh + [self.ziel, f"rm {self.pfad}/{name}"], "Loeschen auf der Storage Box gescheitert", 120)


def box():
    ziel = os.environ.get("AKTE_STORAGEBOX_ZIEL", "")
    pfad = os.environ.get("AKTE_STORAGEBOX_PFAD", "akte-backups")
    if not ziel:
        raise SicherungsFehler("AKTE_STORAGEBOX_ZIEL fehlt in der Umgebung")
    if ziel.startswith("/"):
        return OrdnerBox(str(Path(ziel) / pfad))
    key = os.environ.get("STORAGEBOX_KEY") or "/root/.ssh/storagebox"
    return StorageBox(ziel, pfad, key)


# ------------------------------------------------------------ Paket

def zeit_aus_name(name: str) -> datetime | None:
    m = re.search(r"(\d{8})-(\d{6})", name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _sha(daten: bytes) -> str:
    return hashlib.sha256(daten).hexdigest()


def zeilen_zaehlen(engine) -> dict[str, int]:
    zeilen = {}
    with engine.connect() as c:
        for t in sorted(inspect(engine).get_table_names()):
            zeilen[t] = int(c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() or 0)
    return zeilen


def datenbank_dump(engine) -> bytes:
    url = str(engine.url)
    if url.startswith("sqlite"):
        pfad = engine.url.database
        import sqlite3
        con = sqlite3.connect(pfad)
        try:
            return ("\n".join(con.iterdump()) + "\n").encode()
        finally:
            con.close()
    uri = re.sub(r"^postgresql\+\w+://", "postgresql://", url)
    erg = subprocess.run(["pg_dump", "--no-owner", "--no-privileges", "--format=plain", "--dbname", uri],
                         check=True, capture_output=True, timeout=600)
    return erg.stdout


def dateien_erfassen(basis: Path) -> dict[str, dict]:
    erfasst = {}
    for ordner in DATEI_ORDNER:
        wurzel = basis / ordner
        if not wurzel.is_dir():
            continue
        for p in sorted(wurzel.rglob("*")):
            if p.is_file():
                daten = p.read_bytes()
                erfasst[str(p.relative_to(basis))] = {"groesse": len(daten), "sha256": _sha(daten)}
    return erfasst


def paket_bauen(engine, basis: Path | None = None) -> tuple[str, bytes, dict]:
    """Rueckgabe: (dateiname, verschluesseltes Paket, kopf)."""
    basis = basis or E.DATEN
    zeit = db.jetzt()
    dump = datenbank_dump(engine)
    dateien = dateien_erfassen(basis)
    kopf = {"dienst": "AKTE", "version": E.VERSION, "zeit": zeit.isoformat(), "zeilen": zeilen_zaehlen(engine),
            "pflicht": pflichttabellen(), "dateien": dateien, "abzug": _sha(dump)}
    puffer = io.BytesIO()
    with tarfile.open(fileobj=puffer, mode="w:gz") as tar:
        def _add(name: str, daten: bytes):
            info = tarfile.TarInfo(name)
            info.size, info.mtime = len(daten), int(zeit.timestamp())
            tar.addfile(info, io.BytesIO(daten))
        _add("kopf.json", json.dumps(kopf, ensure_ascii=False, indent=1).encode())
        _add("datenbank.sql", dump)
        for rel in dateien:
            _add("dateien/" + rel, (basis / rel).read_bytes())
    name = f"akte-{zeit.strftime('%Y%m%d-%H%M%S')}.sich"
    return name, verschluesseln(puffer.getvalue(), schluessel()), kopf


def paket_oeffnen(paket: bytes) -> tuple[dict, tarfile.TarFile]:
    roh = entschluesseln(paket, schluessel())
    tar = tarfile.open(fileobj=io.BytesIO(roh), mode="r:gz")
    try:
        kopf = json.loads(tar.extractfile("kopf.json").read())
    except (KeyError, TypeError, json.JSONDecodeError) as ex:
        raise SicherungsFehler("Paket ohne lesbaren Kopf") from ex
    return kopf, tar


def zeilen_im_dump(dump: str) -> dict[str, int]:
    """Zaehlt Zeilen je Tabelle im Dump nach: COPY-Bloecke (pg_dump) oder INSERT-Zeilen (sqlite)."""
    zeilen: dict[str, int] = {}
    aktuell = None
    for zeile in dump.splitlines():
        if aktuell is not None:
            if zeile == "\\.":
                aktuell = None
            else:
                zeilen[aktuell] = zeilen.get(aktuell, 0) + 1
            continue
        m = re.match(r'^COPY (?:\w+\.)?"?(\w+)"? \(.*\) FROM stdin;', zeile)
        if m:
            aktuell = m.group(1)
            zeilen.setdefault(aktuell, 0)
            continue
        m = re.match(r'^INSERT INTO "?(\w+)"? ', zeile)
        if m:
            zeilen[m.group(1)] = zeilen.get(m.group(1), 0) + 1
    return zeilen


# ------------------------------------------------------------ Laeufe

@dataclass
class Befund:
    ok: bool
    text: str
    maengel: list[str] = field(default_factory=list)


SATZ = {
    ("Sicherung", False): "Die taegliche Sicherung von AKTE hat nicht geklappt.",
    ("Rueckholprobe", False): "Die Rueckholprobe von AKTE hat nicht geklappt. Die Sicherungen laufen weiter.",
    ("Rueckholprobe", True): "Rueckholprobe der AKTE-Sicherung: in Ordnung.",
}


def _melden(titel: str, text_: str, ok: bool) -> None:
    """Logbuch immer. Rueckholprobe meldet IMMER per Push (fester Satz, wer montags nichts hoert, weiss Bescheid).
    Fehler gehen zusaetzlich per Mail an alle Berater."""
    try:
        with db.sitzung() as s:
            db.logbuch(s, "sicherung" if ok else "sicherung_fehler", f"{titel}: {text_}")
            satz = SATZ.get((titel, ok))
            if satz:
                import push
                from melden import berater_melden
                for b in s.scalars(db.select(db.Berater).where(db.Berater.aktiv == True)).all():  # noqa: E712
                    if ok:
                        push.senden(s, "berater", b.id, "AKTE Sicherung", satz, "/berater")
                    else:
                        berater_melden(s, b, f"AKTE {titel} FEHLGESCHLAGEN", satz + " " + text_, "/berater")
            s.commit()
    except Exception as ex:  # noqa: BLE001 - Melden darf den Lauf nicht kippen
        print(f"(Meldung nicht moeglich: {ex})", file=sys.stderr)


def taeglich(engine=None, ablage=None, basis: Path | None = None, jetzt: datetime | None = None) -> Befund:
    engine = engine or db._engine or db.verbinden()
    jetzt = jetzt or db.jetzt()
    try:
        ablage = ablage or box()
        name, paket, kopf = paket_bauen(engine, basis)
        # Gegenprobe VOR dem Hochladen: laesst sich das frische Paket wieder oeffnen?
        k2, _ = paket_oeffnen(paket)
        if k2.get("abzug") != kopf["abzug"]:
            raise SicherungsFehler("Das frische Paket laesst sich nicht wieder oeffnen")
        # lokale Kopie (verschluesselt), dann auf die Box
        lokal = Path(os.environ.get("AKTE_SICHERUNG_DIR") or "/var/backups/akte") if basis is None else (basis / "sicherung")
        lokal.mkdir(parents=True, exist_ok=True)
        try:
            lokal.chmod(0o700)
        except OSError:
            pass
        p = lokal / name
        p.write_bytes(paket)
        p.chmod(0o600)
        ablage.hochladen(p, name)
        # Ein Rueckgabewert 0 ist kein Beweis: nachsehen, ob die Datei DORT liegt
        if name not in [n for n, _ in ablage.liste()]:
            raise SicherungsFehler(f"{name} fehlt nach dem Hochladen auf der Box")
        # alte Staende nach Frist entfernen (Box und lokal)
        geloescht = 0
        for alt, _ in ablage.liste():
            z = zeit_aus_name(alt)
            if MUSTER.match(alt) and z and jetzt - z > timedelta(days=AUFBEWAHRUNG_TAGE):
                ablage.loeschen(alt)
                geloescht += 1
        for alt_p in lokal.glob("akte-*.sich"):
            z = zeit_aus_name(alt_p.name)
            if z and jetzt - z > timedelta(days=AUFBEWAHRUNG_TAGE):
                alt_p.unlink(missing_ok=True)
        text_ = (f"{name}: {sum(kopf['zeilen'].values())} Zeilen in {len(kopf['zeilen'])} Tabellen, "
                 f"{len(kopf['dateien'])} Dateien, {len(paket) // 1024} KB, {geloescht} alte entfernt")
        _melden("Sicherung", text_, True)
        return Befund(True, text_)
    except Exception as ex:  # noqa: BLE001
        text_ = f"{type(ex).__name__}: {ex}"
        _melden("Sicherung", text_, False)
        return Befund(False, text_, [text_])


def rueckholprobe(engine=None, ablage=None, jetzt: datetime | None = None) -> Befund:
    engine = engine or db._engine or db.verbinden()
    jetzt = jetzt or db.jetzt()
    maengel: list[str] = []
    try:
        ablage = ablage or box()
        kandidaten = [(zeit_aus_name(n), n) for n, _ in ablage.liste() if MUSTER.match(n) and zeit_aus_name(n)]
        if not kandidaten:
            raise SicherungsFehler("Keine Sicherung auf der Box")
        zeit, name = max(kandidaten)
        alter = jetzt - zeit
        if alter > timedelta(hours=HOECHSTALTER_STUNDEN):
            maengel.append(f"Juengste Sicherung {name} ist {alter.total_seconds() / 3600:.0f} h alt (Grenze {HOECHSTALTER_STUNDEN} h)")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / name
            ablage.holen(name, p)
            kopf, tar = paket_oeffnen(p.read_bytes())
            # 1) Pflichttabellen und Zeilen
            dump = tar.extractfile("datenbank.sql").read()
            if _sha(dump) != kopf.get("abzug"):
                maengel.append("Abzug des Dumps stimmt nicht mit dem Kopf ueberein")
            gezaehlt = zeilen_im_dump(dump.decode("utf-8", "replace"))
            for t in pflichttabellen():
                if t not in kopf.get("zeilen", {}):
                    maengel.append(f"Pflichttabelle {t} fehlt im Kopf")
                elif gezaehlt.get(t, 0) != kopf["zeilen"][t]:
                    maengel.append(f"Tabelle {t}: Kopf sagt {kopf['zeilen'][t]} Zeilen, Dump hat {gezaehlt.get(t, 0)}")
            # 2) Dateien: jede nach Groesse und Hash, keine darf leer sein
            namen = set(tar.getnames())
            geprueft = 0
            for rel, meta in kopf.get("dateien", {}).items():
                if meta.get("groesse", 0) <= 0:
                    maengel.append(f"Datei {rel} ist leer (0 Bytes)")
                    continue
                if "dateien/" + rel not in namen:
                    maengel.append(f"Datei {rel} fehlt im Paket")
                    continue
                daten = tar.extractfile("dateien/" + rel).read()
                if len(daten) != meta["groesse"] or _sha(daten) != meta["sha256"]:
                    maengel.append(f"Datei {rel}: Inhalt weicht vom Kopf ab")
                else:
                    geprueft += 1
            # 3) Leere Sicherung: Datenbank kennt Dateien, Paket nicht
            with engine.connect() as c:
                erwartet = int(c.execute(text("SELECT count(*) FROM unterlage WHERE datei <> ''")).scalar() or 0)
            if erwartet and geprueft == 0:
                maengel.append(f"Datenbank kennt {erwartet} Unterlagendateien, im Paket wurde keine verifiziert")
        text_ = f"{name} ({alter.total_seconds() / 3600:.1f} h alt): {geprueft} Dateien verifiziert, " \
                f"{len(pflichttabellen())} Pflichttabellen" + (f", {len(maengel)} Maengel" if maengel else ", alles stimmt")
        _melden("Rueckholprobe", text_ + ("; " + "; ".join(maengel) if maengel else ""), not maengel)
        return Befund(not maengel, text_, maengel)
    except Exception as ex:  # noqa: BLE001
        text_ = f"{type(ex).__name__}: {ex}"
        _melden("Rueckholprobe", text_, False)
        return Befund(False, text_, maengel + [text_])


if __name__ == "__main__":
    modus = sys.argv[1] if len(sys.argv) > 1 else ""
    if modus == "liste":
        for n, z in sorted(box().liste(), key=lambda x: x[1], reverse=True):
            print(datetime.fromtimestamp(z).strftime("%Y-%m-%d %H:%M"), n)
        sys.exit(0)
    if modus not in ("taeglich", "rueckholprobe"):
        print(__doc__)
        sys.exit(2)
    db.verbinden()
    b = taeglich() if modus == "taeglich" else rueckholprobe()
    print(("OK   " if b.ok else "ROT  ") + modus + ": " + b.text)
    for m in b.maengel:
        print("  - " + m)
    sys.exit(0 if b.ok else 1)
