"""Zeitgesteuerte Aufgaben. Wird stuendlich vom systemd-Timer aufgerufen (akte-zeitplan.timer).

Alle Aufgaben sind idempotent: jede merkt sich am Datensatz, wann sie zuletzt gelaufen ist.
"""
import sys
from datetime import date, timedelta

import einstellungen as E
from db import Vorgang, Unterlage, jetzt, logbuch, select, sitzung, verbinden
from melden import kunde_melden, berater_melden

OFFEN = ("fehlt", "selbst", "angefragt", "abgelehnt")


def lauf(s, heute: date | None = None) -> list[str]:
    heute = heute or date.today()
    getan: list[str] = []
    aktiv = s.scalars(select(Vorgang).where(Vorgang.status.in_(("beratung", "sammeln")))).all()

    for v in aktiv:
        k, b = v.kunde, v.berater
        rest = (v.zins_gueltig_bis - heute).days if v.zins_gueltig_bis else None

        # 1) Zinsdatum fehlt -> woechentlich an den Berater
        if v.zins_gueltig_bis is None:
            if v.zins_wochen_erinnert_am is None or (heute - v.zins_wochen_erinnert_am).days >= E.ERINNERUNG_WOECHENTLICH_TAGE:
                berater_melden(s, b, "Zinsdatum fehlt",
                               f"Fuer {k.name} ist kein Ablaufdatum der Zinskondition eingetragen. Bitte nachtragen.",
                               f"/berater/vorgang/{v.id}", vorgang_id=v.id)
                v.zins_wochen_erinnert_am = heute
                getan.append(f"zinsdatum_fehlt:{v.id}")
        # 2) Einen Tag vor Ablauf -> Berater und Kunde
        elif rest == 1 and v.zins_erinnert_am != heute:
            berater_melden(s, b, "Zinskondition laeuft morgen ab",
                           f"Die Kondition fuer {k.name} ({v.bank or 'Bank'}) laeuft morgen ab.",
                           f"/berater/vorgang/{v.id}", vorgang_id=v.id)
            kunde_melden(s, k, "Deine Zinskondition laeuft morgen ab",
                         "Bitte lade fehlende Unterlagen heute noch hoch oder sprich mit deinem Berater.", "/app")
            v.zins_erinnert_am = heute
            getan.append(f"zins_morgen:{v.id}")
        # 3) Abgelaufen -> woechentlich an den Berater, bis ein neues Datum gesetzt ist
        elif rest is not None and rest < 0:
            if v.zins_wochen_erinnert_am is None or (heute - v.zins_wochen_erinnert_am).days >= E.ERINNERUNG_WOECHENTLICH_TAGE:
                berater_melden(s, b, "Zinskondition abgelaufen",
                               f"Die Kondition fuer {k.name} ist seit {-rest} Tagen abgelaufen. "
                               f"Bitte neues Angebot pruefen, dem Kunden einspielen und neues Datum setzen.",
                               f"/berater/vorgang/{v.id}", vorgang_id=v.id)
                v.zins_wochen_erinnert_am = heute
                getan.append(f"zins_abgelaufen:{v.id}")

        # 4) Hilfe abgelehnt, Unterlagen noch offen -> woechentlich "Soll ich doch helfen?"
        if v.hilfe_abgelehnt_am and any(u.status in OFFEN for u in v.unterlagen):
            if v.hilfe_erinnert_am is None or (heute - v.hilfe_erinnert_am).days >= E.ERINNERUNG_WOECHENTLICH_TAGE:
                kunde_melden(s, k, "Soll dein Berater doch helfen?",
                             "Es fehlen noch Unterlagen. Dein Berater kann sie fuer dich besorgen, damit die Zinskondition haelt.",
                             f"/app/beschaffung")
                v.hilfe_erinnert_am = heute
                getan.append(f"hilfe_erinnerung:{v.id}")

    # 5) Nachfrage nach der Makler-Mail (2 Tage)
    faellig = s.scalars(select(Unterlage).where(Unterlage.status == "angefragt",
                                                Unterlage.nachfrage_am <= jetzt(),
                                                Unterlage.nachfrage_gesendet_am.is_(None))).all()
    je_vorgang: dict[int, list[Unterlage]] = {}
    for u in faellig:
        je_vorgang.setdefault(u.vorgang_id, []).append(u)
    for vid, liste in je_vorgang.items():
        v = s.get(Vorgang, vid)
        if v is None or v.status not in ("beratung", "sammeln"):
            continue
        kunde_melden(s, v.kunde, "Ist die Antwort vom Makler da?",
                     f"Vor {E.NACHFRAGE_MAKLER_TAGE} Tagen hast du den Makler um {len(liste)} Unterlage(n) gebeten. Bitte sag uns, ob sie da sind.",
                     f"/app/nachfrage")
        for u in liste:
            u.nachfrage_gesendet_am = jetzt()
        getan.append(f"nachfrage_makler:{vid}")

    if getan:
        logbuch(s, "zeitplan", ", ".join(getan))
    s.commit()
    return getan


if __name__ == "__main__":
    verbinden()
    with sitzung() as s:
        ergebnis = lauf(s)
    print(f"zeitplan: {len(ergebnis)} Aufgaben: {', '.join(ergebnis) or 'nichts faellig'}")
    sys.exit(0)
