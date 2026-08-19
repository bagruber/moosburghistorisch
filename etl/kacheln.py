"""Entzerrt die Blattscans nach Web Mercator und schreibt je Jahrgang
eine PMTiles-Datei mit Rasterkacheln.

Der Weg jedes Ausgabepixels: Web Mercator -> WGS84 -> Gauss-Krueger Zone 4
(mit Datumsuebergang, den pyproj besorgt) -> Blattpixel ueber die Affin-
abbildung aus georef.py. Gerechnet wird das exakt nur auf einem groben Netz;
dazwischen wird linear interpoliert, weil die Abbildung ueber wenige hundert
Pixel praktisch affin ist. Das spart den Grossteil der Projektionsrechnung,
ohne messbar ungenauer zu werden.

Beschnitten wird auf den Blattschnitt selbst, nicht auf den Scanrand: damit
verschwinden Rahmen, Randleiste und Legende, und die unterschiedlichen
Layouts der Faltkarten spielen keine Rolle mehr.
"""
import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer
from pyproj import Transformer
from scipy import ndimage

import georef

Image.MAX_IMAGE_PIXELS = None
HIER = Path(__file__).parent
ZIEL = HIER.parent / "public" / "data"

MINZOOM, MAXZOOM = 10, 16
KACHEL = 256
NETZ = 16          # Stuetzweite des groben Rechennetzes in Pixeln
RANDABZUG = 9      # Blattschnitt so weit einruecken, dass der Rahmen wegfaellt
GUETE = 72         # WebP-Qualitaet
# Scanaufloesung in Web-Mercator-Metern je Pixel: 300 dpi bei 1:25000 sind
# 2,117 m am Boden, in Mercator um 1/cos(Breite) gestreckt.
QUELLE_MERC = 2.117 / math.cos(math.radians(48.45))

nach_gk = Transformer.from_crs("EPSG:4326", "EPSG:31468", always_xy=True)


def mercator_grenzen():
    """Kartenfeld in Web-Mercator-Metern."""
    nach_merc = Transformer.from_crs("EPSG:4314", "EPSG:3857", always_xy=True)
    ecken = [nach_merc.transform(lon, lat)
             for lon in (georef.WEST, georef.OST)
             for lat in (georef.SUED, georef.NORD)]
    xs, ys = zip(*ecken)
    return min(xs), min(ys), max(xs), max(ys)


def kachelbereich(z, grenzen):
    """Kachelindizes, die das Kartenfeld bei Zoom z ueberdecken."""
    umfang = 2 * math.pi * 6378137.0
    n = 2 ** z
    tx0 = int((grenzen[0] + umfang / 2) / umfang * n)
    tx1 = int((grenzen[2] + umfang / 2) / umfang * n)
    ty0 = int((umfang / 2 - grenzen[3]) / umfang * n)
    ty1 = int((umfang / 2 - grenzen[1]) / umfang * n)
    return tx0, ty0, tx1, ty1


def stuetznetz(z, tx0, ty0, breite, hoehe, rueck):
    """Blattpixelkoordinaten auf einem groben Netz ueber dem Kachelblock."""
    umfang = 2 * math.pi * 6378137.0
    aufloesung = umfang / (2 ** z * KACHEL)
    sx = np.arange(0, breite + NETZ, NETZ)
    sy = np.arange(0, hoehe + NETZ, NETZ)
    mx = -umfang / 2 + (tx0 * KACHEL + sx) * aufloesung
    my = umfang / 2 - (ty0 * KACHEL + sy) * aufloesung
    gx, gy = np.meshgrid(mx, my)
    lon = gx / 6378137.0 * 180 / math.pi
    lat = (2 * np.arctan(np.exp(gy / 6378137.0)) - math.pi / 2) * 180 / math.pi
    E, N = nach_gk.transform(lon.ravel(), lat.ravel())
    uv = rueck(np.array(E), np.array(N))
    return uv[0].reshape(gx.shape), uv[1].reshape(gx.shape)


def ruecktransform(modell):
    """GK -> Blattpixel, vektorisiert."""
    A = np.array([modell["ostachse"][:2], modell["nordachse"][:2]])
    b = np.array([modell["ostachse"][2], modell["nordachse"][2]])
    Ai = np.linalg.inv(A)

    def f(E, N):
        d = np.stack([E - b[0], N - b[1]])
        return Ai @ d
    return f


def mipmaps(bild):
    """Verkleinerungsstufen des Scans, damit tiefe Zoomstufen nicht flimmern."""
    stufen = [np.asarray(bild, dtype=np.uint8)]
    aktuell = bild
    while min(aktuell.size) > 64:
        aktuell = aktuell.resize((aktuell.width // 2, aktuell.height // 2), Image.BOX)
        stufen.append(np.asarray(aktuell, dtype=np.uint8))
    return stufen


def abtasten(bild, u, v):
    """Bilineare Abtastung."""
    H, W = bild.shape[:2]
    u0 = np.clip(np.floor(u).astype(np.int32), 0, W - 2)
    v0 = np.clip(np.floor(v).astype(np.int32), 0, H - 2)
    fu = (u - u0)[..., None]
    fv = (v - v0)[..., None]
    oben = bild[v0, u0] * (1 - fu) + bild[v0, u0 + 1] * fu
    unten = bild[v0 + 1, u0] * (1 - fu) + bild[v0 + 1, u0 + 1] * fu
    return oben * (1 - fv) + unten * fv


def feldmaske(ecken, u, v, abzug=RANDABZUG):
    """Punkte innerhalb des um den Rahmen eingerueckten Blattschnitts."""
    mitte = np.mean([ecken[k] for k in ecken], axis=0)
    drin = np.ones(u.shape, bool)
    for a, b in (("nw", "no"), ("no", "so"), ("so", "sw"), ("sw", "nw")):
        p0, p1 = np.array(ecken[a]), np.array(ecken[b])
        n = np.array([-(p1 - p0)[1], (p1 - p0)[0]], float)
        n /= np.linalg.norm(n)
        if n @ (mitte - p0) < 0:
            n = -n
        drin &= (n[0] * (u - p0[0]) + n[1] * (v - p0[1])) > abzug
    return drin


def blatt_kacheln(jahr, modell):
    scan = Image.open(HIER / "scans" / modell["datei"]).convert("RGB")
    stufen = mipmaps(scan)
    ecken = {k: np.array(v, float) for k, v in modell["kartenfeld"].items()}
    rueck = ruecktransform(modell)
    grenzen = mercator_grenzen()
    umfang = 2 * math.pi * 6378137.0

    kacheln = {}
    for z in range(MINZOOM, MAXZOOM + 1):
        tx0, ty0, tx1, ty1 = kachelbereich(z, grenzen)
        breite = (tx1 - tx0 + 1) * KACHEL
        hoehe = (ty1 - ty0 + 1) * KACHEL
        netz_u, netz_v = stuetznetz(z, tx0, ty0, breite, hoehe, rueck)
        # Stufe waehlen, deren Aufloesung knapp feiner ist als die Zielkachel
        ziel = umfang / (2 ** z * KACHEL) / QUELLE_MERC
        stufe = min(max(int(math.floor(math.log2(max(ziel, 1.0)))), 0), len(stufen) - 1)
        teiler = 2 ** stufe
        quelle = stufen[stufe]

        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                px = (tx - tx0) * KACHEL
                py = (ty - ty0) * KACHEL
                ziele = np.mgrid[py:py + KACHEL, px:px + KACHEL] / NETZ
                u = ndimage.map_coordinates(netz_u, ziele, order=1, mode="nearest")
                v = ndimage.map_coordinates(netz_v, ziele, order=1, mode="nearest")
                drin = feldmaske(ecken, u, v)
                if not drin.any():
                    continue
                farbe = abtasten(quelle, u / teiler, v / teiler)
                bild = np.zeros((KACHEL, KACHEL, 4), np.uint8)
                bild[..., :3] = np.clip(farbe, 0, 255).astype(np.uint8)
                bild[..., 3] = np.where(drin, 255, 0)
                puffer = io.BytesIO()
                if drin.all():
                    Image.fromarray(bild[..., :3]).save(
                        puffer, "WEBP", quality=GUETE, method=6)
                else:
                    Image.fromarray(bild).save(
                        puffer, "WEBP", quality=GUETE, method=6)
                kacheln[(z, tx, ty)] = puffer.getvalue()
    return kacheln, grenzen


def schreibe(jahr, kacheln, grenzen):
    nach_wgs = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    lon0, lat0 = nach_wgs.transform(grenzen[0], grenzen[1])
    lon1, lat1 = nach_wgs.transform(grenzen[2], grenzen[3])
    ZIEL.mkdir(parents=True, exist_ok=True)
    pfad = ZIEL / f"{jahr}.pmtiles"
    with open(pfad, "wb") as f:
        w = Writer(f)
        for tileid, daten in sorted((zxy_to_tileid(z, tx, ty), d)
                                    for (z, tx, ty), d in kacheln.items()):
            w.write_tile(tileid, daten)
        w.finalize(
            {
                "tile_type": TileType.WEBP,
                "tile_compression": Compression.NONE,
                "min_zoom": MINZOOM,
                "max_zoom": MAXZOOM,
                "min_lon_e7": int(lon0 * 1e7),
                "min_lat_e7": int(lat0 * 1e7),
                "max_lon_e7": int(lon1 * 1e7),
                "max_lat_e7": int(lat1 * 1e7),
                "center_zoom": 13,
                "center_lon_e7": int((lon0 + lon1) / 2 * 1e7),
                "center_lat_e7": int((lat0 + lat1) / 2 * 1e7),
            },
            {
                "name": f"TK25 Blatt 7537 Moosburg a.d.Isar, Ausgabe {jahr}",
                "attribution": "Bayerische Vermessungsverwaltung",
            },
        )
    return pfad.stat().st_size


def main():
    modelle = json.loads((HIER / "passpunkte.json").read_text(encoding="utf-8"))
    gesamt = 0
    for jahr, modell in sorted(modelle.items()):
        kacheln, grenzen = blatt_kacheln(jahr, modell)
        groesse = schreibe(jahr, kacheln, grenzen)
        gesamt += groesse
        print("%s  %5d Kacheln  %6.1f MB" % (jahr, len(kacheln), groesse / 1e6))
    print("zusammen %.1f MB" % (gesamt / 1e6))


if __name__ == "__main__":
    main()
