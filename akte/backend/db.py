"""Datenmodell und Datenbankzugriff. SQLite fuer Entwicklung, PostgreSQL auf dem Server."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy import (
    create_engine, String, Integer, Float, Boolean, Text, DateTime, Date,
    ForeignKey, select, event,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session,
)

import einstellungen as E


class Basis(DeclarativeBase):
    pass


def jetzt() -> datetime:
    return datetime.now().replace(microsecond=0)


class Organisation(Basis):
    """Vertriebsorganisation. Optional, fuer spaeter."""
    __tablename__ = "organisation"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)


class Berater(Basis):
    __tablename__ = "berater"
    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organisation.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    telefon: Mapped[str] = mapped_column(String(50), default="")
    passwort_hash: Mapped[str] = mapped_column(String(300))
    vertreter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("berater.id"), nullable=True)
    preis_beschaffung: Mapped[float] = mapped_column(Float, default=0.0)  # Pauschale je Unterlage in EUR
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)

    vorgaenge: Mapped[list["Vorgang"]] = relationship(back_populates="berater", foreign_keys="Vorgang.berater_id")


class Kunde(Basis):
    __tablename__ = "kunde"
    id: Mapped[int] = mapped_column(primary_key=True)
    berater_id: Mapped[int] = mapped_column(ForeignKey("berater.id"))
    vorname: Mapped[str] = mapped_column(String(100))
    nachname: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200))
    telefon: Mapped[str] = mapped_column(String(50), default="")
    adresse: Mapped[str] = mapped_column(Text, default="")
    herkunft: Mapped[str] = mapped_column(String(30), default="berater")  # homepage | makler | privat | berater
    beschaeftigung: Mapped[str] = mapped_column(String(30), default="")   # angestellt | selbstaendig
    netto_1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    netto_2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    netto_3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    onboarding_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    anmeldelink: Mapped[str] = mapped_column(String(80), default="", index=True)
    anmeldelink_bis: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    letzter_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    app_installiert_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)

    vorgaenge: Mapped[list["Vorgang"]] = relationship(back_populates="kunde")

    @property
    def name(self) -> str:
        return f"{self.vorname} {self.nachname}".strip()


class Vorgang(Basis):
    """Ein Finanzierungsfall: ein Objekt, ein Bankangebot, eine Unterlagenliste."""
    __tablename__ = "vorgang"
    id: Mapped[int] = mapped_column(primary_key=True)
    kunde_id: Mapped[int] = mapped_column(ForeignKey("kunde.id"))
    berater_id: Mapped[int] = mapped_column(ForeignKey("berater.id"))
    bezeichnung: Mapped[str] = mapped_column(String(200), default="")  # z. B. Objektadresse
    bank: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(30), default="beratung")
    # beratung | sammeln | freigegeben | exportiert | abgeschlossen | abgebrochen
    zins_gueltig_bis: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    zins_erinnert_am: Mapped[Optional[date]] = mapped_column(Date, nullable=True)       # 1 Tag vorher
    zins_wochen_erinnert_am: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # woechentlich
    modernisierung: Mapped[bool] = mapped_column(Boolean, default=False)
    modernisierung_betrag: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    liste_datei: Mapped[str] = mapped_column(String(400), default="")
    liste_hochgeladen_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    beteiligte_erfasst_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    hilfe_abgelehnt_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    hilfe_erinnert_am: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    vollmacht_berater_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # Kunde hat Berater bevollmaechtigt
    vollmacht_berater_datei: Mapped[str] = mapped_column(String(400), default="")
    freigabe_kunde_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    freigabe_schriftlich: Mapped[bool] = mapped_column(Boolean, default=False)  # Berater hat schriftliche Bestaetigung
    exportiert_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)

    kunde: Mapped["Kunde"] = relationship(back_populates="vorgaenge")
    berater: Mapped["Berater"] = relationship(back_populates="vorgaenge", foreign_keys=[berater_id])
    unterlagen: Mapped[list["Unterlage"]] = relationship(back_populates="vorgang", order_by="Unterlage.reihenfolge")
    beteiligte: Mapped[list["Beteiligter"]] = relationship(back_populates="vorgang")

    # --- abgeleitete Werte ---
    @property
    def zins_tage_rest(self) -> Optional[int]:
        if not self.zins_gueltig_bis:
            return None
        return (self.zins_gueltig_bis - date.today()).days

    @property
    def zins_abgelaufen(self) -> bool:
        r = self.zins_tage_rest
        return r is not None and r < 0

    @property
    def vollmacht_vorhanden(self) -> bool:
        return self.vollmacht_berater_am is not None

    def unterlagen_erforderlich(self) -> list["Unterlage"]:
        return [u for u in self.unterlagen if u.status != "nicht_erforderlich"]

    @property
    def alles_akzeptiert(self) -> bool:
        erf = self.unterlagen_erforderlich()
        return bool(erf) and all(u.status == "akzeptiert" for u in erf)

    @property
    def freigegeben(self) -> bool:
        return self.freigabe_kunde_am is not None or self.freigabe_schriftlich

    @property
    def export_moeglich(self) -> bool:
        return self.alles_akzeptiert and self.freigegeben

    @property
    def fortschritt(self) -> tuple[int, int]:
        erf = self.unterlagen_erforderlich()
        return sum(1 for u in erf if u.status == "akzeptiert"), len(erf)


class Beteiligter(Basis):
    __tablename__ = "beteiligter"
    id: Mapped[int] = mapped_column(primary_key=True)
    vorgang_id: Mapped[int] = mapped_column(ForeignKey("vorgang.id"))
    rolle: Mapped[str] = mapped_column(String(30))  # makler | verkaeufer | notar | architekt | handwerker
    name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    adresse: Mapped[str] = mapped_column(Text, default="")
    gewerk: Mapped[str] = mapped_column(String(100), default="")

    vorgang: Mapped["Vorgang"] = relationship(back_populates="beteiligte")


# Status einer Unterlage
STATUS = {
    "fehlt": "fehlt",
    "angefragt": "beim Makler angefragt",
    "selbst": "besorgst du selbst",
    "beauftragt": "Berater besorgt",
    "hochgeladen": "hochgeladen, wird geprueft",
    "abgelehnt": "abgelehnt",
    "wartet_freigabe": "wartet auf Beraterfreigabe",
    "akzeptiert": "akzeptiert",
    "nicht_erforderlich": "nicht erforderlich",
}


class Unterlage(Basis):
    __tablename__ = "unterlage"
    id: Mapped[int] = mapped_column(primary_key=True)
    vorgang_id: Mapped[int] = mapped_column(ForeignKey("vorgang.id"))
    reihenfolge: Mapped[int] = mapped_column(Integer, default=0)
    bezeichnung: Mapped[str] = mapped_column(String(300))           # Text aus der Bankliste
    katalog_typ: Mapped[str] = mapped_column(String(60), default="sonstiges")
    zuordnung_sicher: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="fehlt")
    kritisch: Mapped[bool] = mapped_column(Boolean, default=False)
    preis_beschaffung: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    makler_mail_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    nachfrage_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)   # faellige Nachfrage
    nachfrage_gesendet_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    mahnung_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    datei: Mapped[str] = mapped_column(String(400), default="")
    dateiname: Mapped[str] = mapped_column(String(300), default="")   # von der KI vergebener Name
    hochgeladen_von: Mapped[str] = mapped_column(String(20), default="")  # kunde | berater
    hochgeladen_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ki_ergebnis: Mapped[str] = mapped_column(Text, default="")  # JSON: passt, fehler, zusammenfassung
    fehlerliste: Mapped[str] = mapped_column(Text, default="")  # JSON-Liste von Texten
    berater_kommentar: Mapped[str] = mapped_column(Text, default="")
    geprueft_am: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    versuche: Mapped[int] = mapped_column(Integer, default=0)

    vorgang: Mapped["Vorgang"] = relationship(back_populates="unterlagen")

    @property
    def fehler(self) -> list[str]:
        try:
            return json.loads(self.fehlerliste) if self.fehlerliste else []
        except json.JSONDecodeError:
            return []

    @property
    def status_text(self) -> str:
        return STATUS.get(self.status, self.status)


class Vollmacht(Basis):
    """Vom Kunden in der App unterschriebene Dokumente (Beschaffungsauftrag, Vollmacht Berater)."""
    __tablename__ = "vollmacht"
    id: Mapped[int] = mapped_column(primary_key=True)
    vorgang_id: Mapped[int] = mapped_column(ForeignKey("vorgang.id"))
    art: Mapped[str] = mapped_column(String(40))  # berater | auftrag
    datei: Mapped[str] = mapped_column(String(400))
    unterlagen_ids: Mapped[str] = mapped_column(Text, default="")  # JSON-Liste bei Auftrag
    betrag: Mapped[float] = mapped_column(Float, default=0.0)
    unterschrieben_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)


class PushAbo(Basis):
    __tablename__ = "push_abo"
    id: Mapped[int] = mapped_column(primary_key=True)
    inhaber_art: Mapped[str] = mapped_column(String(10))  # kunde | berater
    inhaber_id: Mapped[int] = mapped_column(Integer)
    endpoint: Mapped[str] = mapped_column(Text)
    p256dh: Mapped[str] = mapped_column(String(300))
    auth: Mapped[str] = mapped_column(String(100))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)
    fehler: Mapped[int] = mapped_column(Integer, default=0)


class Ausgang(Basis):
    """Protokoll aller Mails (Nachweis)."""
    __tablename__ = "ausgang"
    id: Mapped[int] = mapped_column(primary_key=True)
    an: Mapped[str] = mapped_column(String(200))
    betreff: Mapped[str] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text)
    gesendet_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)
    weg: Mapped[str] = mapped_column(String(20), default="")  # smtp | ordner | protokoll
    fehler: Mapped[str] = mapped_column(Text, default="")


class Ereignis(Basis):
    """Logbuch: wer hat wann was ausgeloest. Grundlage fuer Haftungsfragen."""
    __tablename__ = "ereignis"
    id: Mapped[int] = mapped_column(primary_key=True)
    zeit: Mapped[datetime] = mapped_column(DateTime, default=jetzt, index=True)
    vorgang_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    kunde_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    berater_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ausloeser: Mapped[str] = mapped_column(String(20), default="system")  # kunde | berater | system
    art: Mapped[str] = mapped_column(String(60))
    text: Mapped[str] = mapped_column(Text, default="")


class Parameter(Basis):
    __tablename__ = "parameter"
    schluessel: Mapped[str] = mapped_column(String(100), primary_key=True)
    wert: Mapped[str] = mapped_column(Text, default="")


class Muster(Basis):
    """Musterbibliothek: Vorlagen, die der Kunde ausfuellen und unterschreiben kann."""
    __tablename__ = "muster"
    id: Mapped[int] = mapped_column(primary_key=True)
    titel: Mapped[str] = mapped_column(String(200))
    beschreibung: Mapped[str] = mapped_column(Text, default="")
    katalog_typ: Mapped[str] = mapped_column(String(60), default="")
    datei: Mapped[str] = mapped_column(String(400))
    hochgeladen_am: Mapped[datetime] = mapped_column(DateTime, default=jetzt)


# ---------------------------------------------------------------- Zugriff

_engine = None
SessionLocal = None


def verbinden(url: str | None = None):
    """Engine aufbauen und Tabellen anlegen. Wird beim Start und im Selbsttest gerufen."""
    global _engine, SessionLocal
    url = url or E.DATABASE_URL
    kw = {}
    if url.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
    _engine = create_engine(url, future=True, **kw)
    if url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def _fk(dbapi_con, _):
            dbapi_con.execute("PRAGMA foreign_keys=ON")
    Basis.metadata.create_all(_engine)
    SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def sitzung() -> Session:
    if SessionLocal is None:
        verbinden()
    return SessionLocal()


def logbuch(s: Session, art: str, text: str = "", *, vorgang_id=None, kunde_id=None,
            berater_id=None, ausloeser="system") -> Ereignis:
    e = Ereignis(art=art, text=text, vorgang_id=vorgang_id, kunde_id=kunde_id,
                 berater_id=berater_id, ausloeser=ausloeser)
    s.add(e)
    return e


def parameter_lesen(s: Session, schluessel: str, standard: str = "") -> str:
    p = s.get(Parameter, schluessel)
    return p.wert if p else standard


def parameter_setzen(s: Session, schluessel: str, wert: str) -> None:
    p = s.get(Parameter, schluessel)
    if p:
        p.wert = wert
    else:
        s.add(Parameter(schluessel=schluessel, wert=wert))


def neuer_anmeldelink(kunde: Kunde, tage: int = 30) -> str:
    kunde.anmeldelink = secrets.token_urlsafe(32)
    kunde.anmeldelink_bis = jetzt() + timedelta(days=tage)
    return kunde.anmeldelink
