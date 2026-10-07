"""Fotos -> sauberer PDF-Scan. Qualitaetspruefung vor und nach dem Scan.

Weg 2 aus der Planung: der Kunde fotografiert in der App, der Server begradigt,
entfernt Schatten, wandelt in Schwarzweiss und baut ein PDF. Eine Texterkennung
laeuft, wenn ocrmypdf auf dem Server installiert ist.
"""
import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

from PIL import Image, ImageOps, ImageFilter

import einstellungen as E

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - Rueckfall ohne OpenCV
    cv2 = None
    np = None


@dataclass
class Befund:
    ok: bool
    maengel: list[str] = field(default_factory=list)
    schaerfe: float = 0.0
    helligkeit: float = 0.0


def _graustufen(bild: Image.Image) -> Image.Image:
    bild = ImageOps.exif_transpose(bild)
    return bild.convert("L")


def qualitaet(bild_bytes: bytes) -> Befund:
    """Schnelle Messung: Schaerfe (Laplace-Varianz), Helligkeit, Groesse."""
    try:
        bild = Image.open(io.BytesIO(bild_bytes))
        bild.load()
    except Exception:  # noqa: BLE001
        return Befund(False, ["Das Bild konnte nicht gelesen werden."])
    g = _graustufen(bild)
    maengel = []
    if min(g.size) < 600:
        maengel.append("Das Foto ist zu klein. Bitte naeher heran oder hoehere Aufloesung.")
    # Helligkeit
    hist = g.histogram()
    gesamt = sum(hist) or 1
    helligkeit = sum(i * n for i, n in enumerate(hist)) / gesamt
    if helligkeit < E.SCAN_MIN_HELLIGKEIT:
        maengel.append("Das Foto ist zu dunkel. Bitte bei Tageslicht oder mit Lampe fotografieren.")
    elif helligkeit > E.SCAN_MAX_HELLIGKEIT:
        maengel.append("Das Foto ist ueberbelichtet. Bitte ohne Blitz und ohne direkte Lampe.")
    # Schaerfe
    if cv2 is not None:
        arr = np.array(g)
        schaerfe = float(cv2.Laplacian(arr, cv2.CV_64F).var())
    else:
        kanten = g.filter(ImageFilter.FIND_EDGES)
        stat = kanten.histogram()
        n = sum(stat) or 1
        mittel = sum(i * c for i, c in enumerate(stat)) / n
        schaerfe = sum(c * (i - mittel) ** 2 for i, c in enumerate(stat)) / n
    if schaerfe < E.SCAN_MIN_SCHAERFE:
        maengel.append("Das Foto ist unscharf oder verwackelt. Bitte ruhig halten und neu fotografieren.")
    return Befund(not maengel, maengel, schaerfe, helligkeit)


def _begradigen(g: "np.ndarray") -> "np.ndarray":
    """Sucht das groesste Viereck (das Blatt) und entzerrt es. Ohne Treffer: unveraendert."""
    h, w = g.shape[:2]
    skala = 1000.0 / max(h, w)
    klein = cv2.resize(g, None, fx=skala, fy=skala)
    weich = cv2.GaussianBlur(klein, (5, 5), 0)
    kanten = cv2.Canny(weich, 50, 150)
    kanten = cv2.dilate(kanten, np.ones((3, 3), np.uint8), iterations=1)
    konturen, _ = cv2.findContours(kanten, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    beste = None
    for k in sorted(konturen, key=cv2.contourArea, reverse=True)[:5]:
        umfang = cv2.arcLength(k, True)
        naeherung = cv2.approxPolyDP(k, 0.02 * umfang, True)
        if len(naeherung) == 4 and cv2.contourArea(naeherung) > 0.2 * klein.shape[0] * klein.shape[1]:
            beste = naeherung.reshape(4, 2) / skala
            break
    if beste is None:
        return g
    # Ecken sortieren: oben-links, oben-rechts, unten-rechts, unten-links
    s = beste.sum(axis=1)
    d = np.diff(beste, axis=1).ravel()
    ol, ur = beste[np.argmin(s)], beste[np.argmax(s)]
    orr, ul = beste[np.argmin(d)], beste[np.argmax(d)]
    quelle = np.array([ol, orr, ur, ul], dtype="float32")
    breite = int(max(np.linalg.norm(orr - ol), np.linalg.norm(ur - ul)))
    hoehe = int(max(np.linalg.norm(ul - ol), np.linalg.norm(ur - orr)))
    if breite < 300 or hoehe < 300:
        return g
    ziel = np.array([[0, 0], [breite - 1, 0], [breite - 1, hoehe - 1], [0, hoehe - 1]], dtype="float32")
    m = cv2.getPerspectiveTransform(quelle, ziel)
    return cv2.warpPerspective(g, m, (breite, hoehe))


def scannen(bild_bytes: bytes) -> Image.Image:
    """Ein Foto -> eine Scan-Seite (Graustufen, Schatten entfernt, kontrastreich)."""
    bild = _graustufen(Image.open(io.BytesIO(bild_bytes)))
    if cv2 is None:
        bild = ImageOps.autocontrast(bild, cutoff=2)
        return bild.point(lambda p: 255 if p > 160 else (0 if p < 90 else p))
    arr = np.array(bild)
    arr = _begradigen(arr)
    # Schatten entfernen: Hintergrund schaetzen und herausrechnen
    hintergrund = cv2.medianBlur(arr, 41) if min(arr.shape) > 41 else arr
    normiert = cv2.divide(arr, hintergrund, scale=255)
    # Adaptive Schwelle fuer Schwarzweiss-Wirkung, dabei Graustufen fuer Fotos behalten
    sw = cv2.adaptiveThreshold(normiert, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    gemischt = cv2.addWeighted(normiert, 0.35, sw, 0.65, 0)
    return Image.fromarray(gemischt)


def _ocr(pdf_bytes: bytes) -> bytes:
    """Texterkennung mit ocrmypdf, wenn vorhanden. Sonst unveraendert."""
    if not shutil.which("ocrmypdf"):
        return pdf_bytes
    with tempfile.TemporaryDirectory() as d:
        ein, aus = f"{d}/ein.pdf", f"{d}/aus.pdf"
        open(ein, "wb").write(pdf_bytes)
        try:
            subprocess.run(["ocrmypdf", "-l", "deu", "--quiet", ein, aus], check=True, timeout=180)
            return open(aus, "rb").read()
        except Exception:  # noqa: BLE001
            return pdf_bytes


def fotos_zu_pdf(bilder: list[bytes]) -> tuple[bytes | None, list[list[str]]]:
    """Mehrere Fotos -> ein PDF. Rueckgabe (pdf oder None, Maengel je Seite)."""
    seiten, maengel = [], []
    for b in bilder:
        bef = qualitaet(b)
        maengel.append(bef.maengel)
        if bef.ok:
            seite = scannen(b)
            # A4-Verhaeltnis grob halten, Breite auf 1654 px (200 dpi) begrenzen
            if seite.width > 1654:
                seite = seite.resize((1654, int(seite.height * 1654 / seite.width)))
            seiten.append(seite.convert("L"))
    if any(maengel) or not seiten:
        return None, maengel
    puffer = io.BytesIO()
    seiten[0].save(puffer, format="PDF", save_all=True, append_images=seiten[1:], resolution=200.0)
    return _ocr(puffer.getvalue()), maengel
