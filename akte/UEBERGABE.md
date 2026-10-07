# ÜBERGABEPROTOKOLL · AKTE

Stand: 07.10.2026 · Prototyp 0.1.0 · Arbeitstitel "AKTE" (Dossier), Name frei änderbar.

AKTE ist die Unterlagen-App für Baufinanzierungsberater und ihre Kunden. Sie führt den Kunden
durch das Beschaffen aller Bankunterlagen, besonders wenn der Makler schlecht liefert.
Zwei Ansichten: `/berater` (Desktop) und `/app` (PWA fürs Handy).

## Das System misst sich selbst
- `GET /gesund` → `{"ok": true, "seit": ..., "ki": bool, "push": bool}`
- `GET /version` → `{"abdruck": "<16 Zeichen>"}` (Hash aller .py und .html). `ausrollen.sh` vergleicht ihn.
- `backend/selftest.py` → 27 Gates, alle müssen grün sein (`AKTE_NUR=<teil-des-namens>` für ein Gate).
- Ereignisprotokoll in der Tabelle `ereignis`, sichtbar unten auf jeder Vorgangsseite.

## Starten (lokal)
```
cd akte/backend
python3 -m venv .venv && .venv/bin/pip install -r ../requirements.txt
AKTE_BERATER_PASSWORT=test1234 AKTE_BERATER_EMAIL=du@example.org .venv/bin/uvicorn main:app --port 8410
```
Ohne SMTP landen Mails als `.eml` unter `backend/daten/ausgang/`. Der Einstiegslink steht in der Mail.
Ohne `ANTHROPIC_API_KEY` ordnet eine Schlagwort-Heuristik die Bankliste zu, und jeder Upload wartet auf die Beraterfreigabe.

## Ausrollen (Hetzner, reika-portal)
`./ausrollen.sh` von einem Rechner mit dem Key `~/.ssh/reika-portal-hetzner`. Fünf Schritte wie bei MILLER:
Selbsttest lokal, rsync nach `/opt/akte`, venv + systemd (`akte.service`, `akte-zeitplan.timer` stündlich),
Selbsttest auf dem Server, Neustart, Abdruck-Beweis per `/version`.
Vorher einmalig auf dem Server: Postgres-Datenbank `akte` anlegen, `/etc/akte.env` nach `deploy/akte.env.beispiel`
ausfüllen, Caddy-Block aus `deploy/Caddyfile.akte` einhängen, `python push.py schluessel` für VAPID.
Port 8410 ist eine Annahme, auf dem Server prüfen (MILLER hat 8402).
Diese Cloud-Session hatte keinen SSH-Zugang: das Skript ist geschrieben, aber noch nie gelaufen.

## Ablauf, wie gebaut
1. **Vorgang entsteht** per `POST /api/buchung` (Homepage, mit `AKTE_BUCHUNG_SCHLUESSEL`) oder vom Berater unter
   "Neuer Kunde" (Herkunft: Makler, Privat, Homepage, eigener Kontakt). Einstiegsmail mit Anmeldelink (30 Tage).
2. **Onboarding** `/app/start`: Begrüßung mit Beratername, drei Nettogehälter (Selbständige: Durchschnittsgewinn).
   Nur die drei Zahlen werden gespeichert, Berater bekommt eine Meldung.
3. **Beratung**: Berater pflegt Objekt, Bank, Zinsdatum, Modernisierung (ja/nein, Betrag) und lädt die
   Europace-Liste als PDF hoch. KI (oder Heuristik) zerlegt sie in Positionen und ordnet jede dem Katalog in
   `katalog.py` zu. Unsichere Zuordnungen sind orange markiert, ein Klick bestätigt. Erster Upload löst den Push
   "Deine Unterlagenliste ist da" aus.
4. **Beteiligte** `/app/beteiligte`: Makler, Verkäufer, Notar, bei Modernisierung Handwerker (mehrere, mit Gewerk),
   ab 100.000 EUR auch Architekt. Alles optional. Fehlt eine Rolle für offene Unterlagen, folgt die Warnung
   und das Beschaffungsangebot.
5. **Beschaffungsauftrag** `/app/beschaffung`: Kunde wählt einzelne Unterlagen, sieht Preise (Beraterpauschale
   oder Preis je Position), unterschreibt auf dem Canvas. Daraus entsteht ein PDF "Beschaffungsauftrag und
   Vollmacht" (`pdfs.py`), die Unterlagen gehen auf "beauftragt", der Berater darf ab jetzt für den Kunden
   hochladen. "Ich besorge alles selbst" zeigt den Haftungshinweis und startet den wöchentlichen Push
   "Soll dein Berater doch helfen?".
6. **Unterlage** `/app/unterlage/<id>`: Beschaffungsweg aus dem Katalog, Dienstleister-Link (1000hands,
   Energieausweis48), Vorlage "Vollmacht des Verkäufers" (vorausgefüllt mit den Beteiligten), mailto-Link an
   den Makler mit allen offenen Makler-Positionen, Knopf "Ich habe die Mail gesendet" (startet die 2-Tage-Frist),
   Upload als PDF oder Fotos.
7. **Fotos** werden serverseitig gescannt (`scanner.py`: Schärfe, Helligkeit, Kantenerkennung, Entzerrung,
   Schattenentfernung, PDF; OCR wenn `ocrmypdf` installiert). Schlechte Seiten kommen mit Seitenzahl zurück.
8. **Prüfung** (`ki.py`): Bild-PDF ohne Text wird als Foto abgelehnt (außer Objektfotos). KI prüft gegen
   `PRUEFREGELN` je Typ, benennt die Datei. Ergebnis: akzeptiert, abgelehnt mit Fehlerliste, oder
   "wartet auf Beraterfreigabe" bei kritischen Typen (Grundbuchauszug, Wohnflächenberechnung, Grundrisse)
   und immer ohne KI. Berater wird bei jedem Kundenupload per Push und Mail informiert.
9. **Nachfrage** nach 2 Tagen (`zeitplan.py`): Push "Ist die Antwort vom Makler da?" → `/app/nachfrage`
   mit Mahnung (mailto), besorgen lassen, selbst besorgen.
10. **Zinsdatum**: Countdown in der Kunden-App. Berater-Push einen Tag vorher, wöchentlich wenn das Datum
    fehlt, wöchentlich nach Ablauf. Neues Datum setzt die Zähler zurück und informiert den Kunden.
11. **Freigabe und Export**: Sind alle Unterlagen akzeptiert, gibt der Kunde in der App frei, oder der Berater
    setzt den Haken "schriftliche Bestätigung liegt vor". Dann: ZIP mit nummerierten, sprechenden Dateinamen,
    Inhaltsverzeichnis, Freigabenachweis und Vollmachten für Europace.

## Design (Qualitypool)
- Farben aus der Palette, die Tobi sich am 28.04.2026 per Mail "farben" von seiner Qualitypool-Adresse geschickt hat:
  Dunkelgrün #276653 (Kopf, Flächen), Grün #5cbc8c (Fortschritt), Creme #F8F5EE (Hintergrund),
  Gelb #ffe600 (Handlungsknopf mit schwarzer Schrift, wie im Academy-Banner), Mint #70FFB6, Hellgelb #FFF79D.
  Alle Werte stehen als Variablen oben in `static/stil.css`.
- Wortmarke: aus der Mailsignatur (190 px breit, hochskaliert) als `static/qp-wortmarke*.png`. Die Originaldatei liegt
  unter https://www.qualitypool.de/qp/uploads/2023/01/QP-Logo_RGB_black-4.png und sollte die Platzhalter ersetzen.
- Schrift: Die Markenschrift ist nicht enthalten (Lizenz). Die App nutzt Sora/Poppins, falls installiert, sonst Systemschrift.
  Keine Google-Fonts-Einbindung wegen DSGVO; die Schriftdatei bei Bedarf selbst unter `static/` ablegen.
- Rot für Fehler ist nicht Teil der Palette und bewusst gedämpft gehalten.

## Status einer Unterlage
fehlt · angefragt (Makler) · selbst · beauftragt (Berater) · hochgeladen · abgelehnt · wartet_freigabe ·
akzeptiert · nicht_erforderlich. Übergänge nur in `main.py`.

## Dateien
```
akte/
  ausrollen.sh           Ausrollen mit Selbsttest-Gates und Abdruck-Beweis
  requirements.txt
  deploy/                akte.service, akte-zeitplan.service/.timer, Caddyfile.akte, akte.env.beispiel
  backend/
    main.py              alle Routen (Kunde /app, Berater /berater, /api/buchung, /gesund, /version)
    db.py                Datenmodell (SQLAlchemy, SQLite lokal, Postgres auf dem Server), logbuch()
    katalog.py           Unterlagenkatalog: Typ, Quelle, Beschaffungsweg, kritisch, Vollmacht, Schlagworte
    ki.py                Liste lesen, Unterlage prüfen und benennen (Anthropic, mit Rückfall)
    scanner.py           Fotos → PDF-Scan mit Qualitätsprüfung
    pdfs.py              Vollmacht Verkäufer, Auftrag+Vollmacht Berater, Export-ZIP
    post.py              Mail (SMTP oder .eml-Ablage), Mailtexte, Makler-Mailtext
    push.py              Web Push (VAPID), Schlüsselerzeugung
    melden.py            Push zuerst, Mail als Rückfall, immer Logbuch
    zeitplan.py          stündliche Aufgaben (idempotent)
    auth.py              Passwort-Hash, signierte Cookies, Anmeldelinks
    selftest.py          27 Gates
    templates/           Jinja2, deutsch, mobil zuerst
    static/              stil.css, app.js (Push, Installation, Unterschrift, Fotovorschau), sw.js, manifest, Icons
```

## Entscheidungen aus dem Gespräch (CEO 07.10.2026)
- Nur Mail als Kommunikationskanal, Push als Benachrichtigung in der App. Kein WhatsApp, keine SMS.
- Bankliste kommt immer als Europace-PDF, Berater lädt sie jedes Mal hoch, Aufwand minimal.
- Gehaltsnachweise beim Onboarding: Vertrauen, nur drei Zahlen. Nachweise später über die Liste.
- Banken akzeptieren keine Fotos: deshalb Scanner (Weg 2) mit drei Verteidigungslinien.
- Kritisch mit Beraterfreigabe: Wohnflächenberechnung, Grundbuchauszug, Grundrisse.
- Unterschrift in der App reicht (geprüft).
- Warnung bei jeder fehlenden Rolle; Architekt/Handwerker nur bei Modernisierung, Architekt ab 100k.
- Teilweiser Beschaffungsauftrag erlaubt. Ablehnung → Haftungshinweis + wöchentlicher Push (gleicher Takt wie Zinsdatum).
- Keine Europace-API, Export bleibt ZIP. Keine Automatik beim Kaufvertrag-Lesen oder Vollmacht-Vorausfüllen aus Dokumenten.
- Einzelne Berater; Datenmodell hat `organisation` für spätere Vertriebsorganisationen und `vertreter_id` für Urlaub.
- Alles Rechtliche (Beschaffungsgebühr, Haftungstext, Löschfristen, KI-Auftragsverarbeitung) prüft der Anwalt.

## Offen / nächste Schritte
1. Server: Postgres, `/etc/akte.env`, Caddy, VAPID-Schlüssel, `ANTHROPIC_API_KEY`, dann `./ausrollen.sh`.
2. Homepage-Anbindung: `booking.js` öffnet nur Google Calendar. Wer den Termin bucht, muss `POST /api/buchung`
   auslösen (Felder `name|vorname+nachname`, `email`, `telefon`, `schluessel`). Kandidat: JAMES (Terminlogik).
3. Face ID / Passkeys für Kunden (wie SMITH/MILLER): noch nicht gebaut, Login läuft über Anmeldelink + 90-Tage-Cookie.
4. Musterbibliothek befüllen (Berater → Einstellungen). Vollmacht Verkäufer erzeugt die App selbst.
5. Prüfregeln je Typ in `ki.PRUEFREGELN` mit echten Dokumenten schärfen; Scanner-Schwellen mit echten Fotos.
6. `ocrmypdf` + `tesseract-ocr-deu` auf dem Server installieren, dann sind Scans durchsuchbar.
7. Haftungs- und Warntexte durch Anwaltstexte ersetzen (in `templates/kunde_beschaffung.html`, `kunde_home.html`, `pdfs.py`).
8. Löschkonzept: Vorgang abgeschlossen → Dateien nach Frist löschen (noch nicht gebaut).
