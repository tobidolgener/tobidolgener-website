"""Unterlagenkatalog.

Jede Position einer Bank-Unterlagenliste wird auf genau einen Katalogtyp
abgebildet. Am Typ haengen: Quelle, Beschaffungsweg, Kritisch-Kennzeichen
(Beraterfreigabe), Vollmachtsart und Schlagworte fuer die Zuordnung.
"""

from dataclasses import dataclass, field

# Quellen: wer liefert die Unterlage im Normalfall
KUNDE = "kunde"                    # Kunde hat sie selbst (Gehalt, Ausweis ...)
MAKLER = "makler"                  # kommt ueblicherweise vom Makler
VERKAEUFER_VOLLMACHT = "verkaeufer_vollmacht"  # Berater holt sie mit Vollmacht des Verkaeufers
NOTAR = "notar"                    # beim Notar anfordern
GRUNDBUCHAMT = "grundbuchamt"      # Urkunden zu Eintragungen
DIENSTLEISTER = "dienstleister"    # 1000hands, energieausweis48
ARCHITEKT = "architekt"
HANDWERKER = "handwerker"

# Vollmachtsarten
VM_VERKAEUFER = "verkaeufer"       # Vorlage, die der Verkaeufer unterschreibt
VM_BERATER = "berater"             # Kunde bevollmaechtigt den Berater (in der App unterschrieben)


@dataclass
class Typ:
    schluessel: str
    name: str
    kategorie: str                       # persoenlich | objekt | vertrag | modernisierung | sonstiges
    quelle: str
    kritisch: bool = False               # Beraterfreigabe noetig, auch wenn die KI ja sagt
    beschaffung: str = ""                # Text fuer den Kunden: wie besorge ich das selbst
    link: str = ""                       # Dienstleister-Link
    vollmacht: str = ""                  # VM_VERKAEUFER | VM_BERATER | ""
    beauftragbar: bool = False           # kann der Berater das gegen Gebuehr besorgen
    schlagworte: list = field(default_factory=list)
    nur_modernisierung: bool = False     # nur bei Modernisierung
    nur_ab_100k: bool = False            # nur bei Modernisierung ab 100.000 EUR
    nur_selbstaendig: bool = False


TYPEN: list[Typ] = [
    # --- persoenlich ---
    Typ("gehaltsnachweis", "Gehaltsnachweise (letzte 3 Monate)", "persoenlich", KUNDE,
        beschaffung="Vom Arbeitgeber oder aus dem Lohnportal als PDF herunterladen. Fotos werden von der Bank nicht akzeptiert.",
        schlagworte=["gehalt", "lohn", "verdienstabrechnung", "entgelt", "einkommensnachweis", "gehaltsabrechnung"]),
    Typ("personalausweis", "Personalausweis (Vorder- und Rueckseite)", "persoenlich", KUNDE,
        beschaffung="Beide Seiten als PDF-Scan. Nicht als Foto.",
        schlagworte=["ausweis", "personalausweis", "reisepass", "identit"]),
    Typ("kontoauszuege", "Kontoauszuege (letzte 3 Monate)", "persoenlich", KUNDE,
        beschaffung="Im Online-Banking als PDF herunterladen, alle Seiten.",
        schlagworte=["kontoausz", "gehaltskonto", "umsatz"]),
    Typ("eigenkapitalnachweis", "Eigenkapitalnachweis", "persoenlich", KUNDE,
        beschaffung="Aktueller Depot- oder Kontoauszug, Bausparvertrag oder Sparbuch als PDF.",
        schlagworte=["eigenkapital", "depot", "sparbuch", "bauspar", "guthaben", "vermoegen", "vermögen"]),
    Typ("selbstauskunft", "Selbstauskunft", "persoenlich", KUNDE,
        beschaffung="Formular der Bank ausfuellen und unterschreiben. Vorlage in der Musterbibliothek.",
        schlagworte=["selbstauskunft", "schufa"]),
    Typ("steuerbescheid", "Einkommensteuerbescheide (letzte 2 Jahre)", "persoenlich", KUNDE,
        beschaffung="Vom Finanzamt oder Steuerberater als PDF.",
        schlagworte=["steuerbescheid", "einkommensteuer", "est-bescheid"]),
    Typ("bwa", "BWA und Jahresabschluesse", "persoenlich", KUNDE, nur_selbstaendig=True,
        beschaffung="Vom Steuerberater: aktuelle BWA mit Summen- und Saldenliste sowie die letzten zwei Jahresabschluesse.",
        schlagworte=["bwa", "betriebswirtschaftliche", "jahresabschluss", "bilanz", "gewinnermittlung", "eür", "eur"]),
    Typ("rentenauskunft", "Rentenauskunft", "persoenlich", KUNDE,
        beschaffung="Bei der Deutschen Rentenversicherung anfordern oder aus dem letzten Rentenbescheid.",
        schlagworte=["rente", "rentenbescheid", "rentenauskunft", "versorgung"]),
    Typ("bestehende_darlehen", "Nachweise bestehender Darlehen", "persoenlich", KUNDE,
        beschaffung="Darlehensvertrag und aktueller Saldo als PDF.",
        schlagworte=["darlehen", "kredit", "verbindlichkeit", "restschuld", "leasing"]),
    Typ("mietvertrag_vermietung", "Mietvertraege (bei Vermietung)", "persoenlich", KUNDE,
        beschaffung="Aktuelle Mietvertraege und Mietaufstellung.",
        schlagworte=["mietvertr", "mieteinnahme", "mietaufstellung"]),
    # --- objekt ---
    Typ("grundbuchauszug", "Grundbuchauszug (aktuell)", "objekt", VERKAEUFER_VOLLMACHT, kritisch=True,
        beschaffung="Der Verkaeufer unterschreibt die Vollmacht aus der App. Damit holt dein Berater den Auszug beim Grundbuchamt.",
        vollmacht=VM_VERKAEUFER, beauftragbar=True,
        schlagworte=["grundbuch"]),
    Typ("flurkarte", "Flurkarte / Lageplan", "objekt", VERKAEUFER_VOLLMACHT,
        beschaffung="Gleicher Weg wie beim Grundbuch: Vollmacht des Verkaeufers, dein Berater holt die Karte beim Katasteramt.",
        vollmacht=VM_VERKAEUFER, beauftragbar=True,
        schlagworte=["flurkarte", "lageplan", "liegenschaftskarte", "kataster"]),
    Typ("baulastenverzeichnis", "Auszug Baulastenverzeichnis", "objekt", VERKAEUFER_VOLLMACHT,
        beschaffung="Gleicher Weg wie beim Grundbuch: Vollmacht des Verkaeufers, dein Berater holt den Auszug bei der Bauaufsicht.",
        vollmacht=VM_VERKAEUFER, beauftragbar=True,
        schlagworte=["baulast"]),
    Typ("grundriss", "Grundrisse", "objekt", DIENSTLEISTER, kritisch=True,
        beschaffung="Wenn der Makler keine liefert: 1000hands zeichnet Grundrisse aus alten Plaenen oder per Aufmass vor Ort.",
        link="https://www.grundriss.com/", beauftragbar=True,
        schlagworte=["grundriss", "bauzeichnung", "bauplan", "schnitt", "ansicht"]),
    Typ("wohnflaechenberechnung", "Wohnflaechenberechnung", "objekt", DIENSTLEISTER, kritisch=True,
        beschaffung="Wenn der Makler keine liefert: 1000hands berechnet die Wohnflaeche nach WoFlV aus Plaenen oder per Aufmass.",
        link="https://www.grundriss.com/", beauftragbar=True,
        schlagworte=["wohnfl", "wohnflaeche", "flaechenberechnung", "woflv", "nutzfl"]),
    Typ("energieausweis", "Energieausweis", "objekt", DIENSTLEISTER,
        beschaffung="Wenn der Verkaeufer keinen hat: online bestellen bei Energieausweis48 (Qualitypool-Portal).",
        link="https://qualitypool.energieausweis48.de/produktauswahl",
        schlagworte=["energieausweis", "energiepass", "verbrauchsausweis", "bedarfsausweis"]),
    Typ("expose", "Expose / Objektbeschreibung", "objekt", MAKLER,
        beschaffung="Vom Makler oder aus dem Inserat als PDF.",
        schlagworte=["expos", "objektbeschreibung", "beschreibung des objekt"]),
    Typ("objektfotos", "Fotos des Objekts", "objekt", MAKLER,
        beschaffung="Aussenansicht, Wohnraeume, Bad, Kueche. Hier sind Fotos ausdruecklich erwuenscht, als PDF zusammengefasst.",
        schlagworte=["foto", "lichtbild", "bilder"]),
    Typ("baubeschreibung", "Baubeschreibung", "objekt", MAKLER,
        beschaffung="Vom Verkaeufer, Bautraeger oder aus den Bauakten.",
        schlagworte=["baubeschreibung", "bauakte", "baugenehmigung"]),
    Typ("teilungserklaerung", "Teilungserklaerung (Eigentumswohnung)", "objekt", MAKLER,
        beschaffung="Vom Verkaeufer oder der Hausverwaltung. Alternativ beim Grundbuchamt mit Vollmacht.",
        vollmacht=VM_VERKAEUFER, beauftragbar=True,
        schlagworte=["teilungserkl", "aufteilungsplan", "gemeinschaftsordnung"]),
    Typ("weg_protokolle", "WEG-Protokolle und Wirtschaftsplan", "objekt", MAKLER,
        beschaffung="Von der Hausverwaltung: letzte drei Protokolle, Wirtschaftsplan, Hausgeldabrechnung.",
        schlagworte=["weg", "eigentuemerversammlung", "wirtschaftsplan", "hausgeld", "verwalter"]),
    Typ("gebaeudeversicherung", "Wohngebaeudeversicherung", "objekt", MAKLER,
        beschaffung="Versicherungsschein vom Verkaeufer.",
        schlagworte=["gebaeudeversicherung", "gebäudeversicherung", "wohngebaeude", "versicherungsschein"]),
    # --- vertrag ---
    Typ("kaufvertrag", "Kaufvertrag oder Kaufvertragsentwurf", "vertrag", NOTAR,
        beschaffung="Beim Notar anfordern. Der Entwurf reicht fuer die Finanzierung.",
        schlagworte=["kaufvertrag", "vertragsentwurf", "notarvertrag", "entwurf"]),
    Typ("urkunden_abteilung_2", "Urkunden zu Eintragungen in Abteilung II", "vertrag", GRUNDBUCHAMT,
        beschaffung="Nur noetig, wenn im Grundbuch Abteilung II Eintragungen stehen. Die Urkunden gibt das Grundbuchamt heraus, mit Vollmacht des Verkaeufers.",
        vollmacht=VM_VERKAEUFER, beauftragbar=True,
        schlagworte=["abteilung ii", "abteilung 2", "abt. ii", "bewilligung", "urkunde", "wegerecht", "wohnrecht", "niessbrauch", "nießbrauch"]),
    # --- modernisierung ---
    Typ("kostenaufstellung_architekt", "Kostenaufstellung Architekt / Bauingenieur", "modernisierung", ARCHITEKT,
        nur_modernisierung=True, nur_ab_100k=True,
        beschaffung="Bei Modernisierung ab 100.000 EUR: Kostenaufstellung nach Gewerken vom Architekten oder Bauingenieur.",
        schlagworte=["kostenaufstellung", "kostenschaetzung", "kostenschätzung", "architekt", "bauingenieur", "din 276"]),
    Typ("handwerkerangebote", "Handwerkerangebote", "modernisierung", HANDWERKER,
        nur_modernisierung=True,
        beschaffung="Schriftliche Angebote der Handwerker je Gewerk.",
        schlagworte=["handwerker", "angebot", "kostenvoranschlag", "sanierung", "modernisierung", "renovierung"]),
    # --- sonstiges ---
    Typ("vollmacht_verkaeufer", "Vollmacht des Verkaeufers (unterschrieben)", "sonstiges", KUNDE,
        beschaffung="Vorlage aus der App vom Verkaeufer unterschreiben lassen und hier hochladen.",
        schlagworte=["vollmacht verkaeufer", "vollmacht verkäufer"]),
    Typ("sonstiges", "Sonstige Unterlage", "sonstiges", KUNDE,
        beschaffung="Bitte sprich mit deinem Berater, wie du diese Unterlage bekommst.",
        schlagworte=[]),
]

NACH_SCHLUESSEL: dict[str, Typ] = {t.schluessel: t for t in TYPEN}

# Rollen der Beteiligten und welche Katalogtypen sie brauchen
ROLLEN = {
    "makler": "Makler",
    "verkaeufer": "Verkaeufer",
    "notar": "Notar",
    "architekt": "Architekt / Bauingenieur",
    "handwerker": "Handwerker",
}


def typ(schluessel: str) -> Typ:
    return NACH_SCHLUESSEL.get(schluessel, NACH_SCHLUESSEL["sonstiges"])


def zuordnen_heuristisch(bezeichnung: str) -> tuple[str, bool]:
    """Ordnet eine Listenposition per Schlagwort zu. Rueckgabe (schluessel, sicher).

    Dient als Rueckfall, wenn keine KI verfuegbar ist, und als Gegenprobe.
    """
    text = bezeichnung.lower()
    treffer = []
    for t in TYPEN:
        for wort in t.schlagworte:
            if wort in text:
                treffer.append((len(wort), t.schluessel))
                break
    if not treffer:
        return "sonstiges", False
    treffer.sort(reverse=True)
    sicher = len(treffer) == 1 or treffer[0][0] > treffer[1][0] + 2
    return treffer[0][1], sicher


def rollen_fuer_vorgang(modernisierung: bool, betrag: float | None) -> list[str]:
    """Welche Beteiligten werden abgefragt."""
    rollen = ["makler", "verkaeufer", "notar"]
    if modernisierung:
        rollen.append("handwerker")
        if (betrag or 0) >= 100_000:
            rollen.insert(3, "architekt")
    return rollen


def rolle_fuer_typ(t: Typ) -> str | None:
    """Welcher Beteiligte wird fuer diesen Typ gebraucht (fuer Warnungen)."""
    return {
        MAKLER: "makler",
        VERKAEUFER_VOLLMACHT: "verkaeufer",
        GRUNDBUCHAMT: "verkaeufer",
        NOTAR: "notar",
        ARCHITEKT: "architekt",
        HANDWERKER: "handwerker",
    }.get(t.quelle)
