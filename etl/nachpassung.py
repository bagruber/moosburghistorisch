"""Zweiter Durchgang: misst, wie weit das gedruckte Kartenbild eines Blattes
von seinem eigenen gedruckten Gitter abweicht, und legt dafuer eine
Korrektur in passpunkte.json ab.

georef.py fasst jedes Blatt ueber sein Kilometergitter -- das ist die
richtige Grundlage, und sie sitzt auf allen acht Blaettern auf wenige Meter.
Auf den aelteren Ausgaben stimmt aber das Kartenbild nicht ueberall mit dem
Gitter ueberein, das danebengedruckt wurde: Papier zieht sich zwischen den
Druckgaengen der einzelnen Farbplatten, und Nachdrucke entstanden aus neu
fotografierten Vorlagen. Wer Ausgaben uebereinanderlegt, vergleicht das
Kartenbild und nicht das Gitter -- also muss das Kartenbild passen.

Gemessen wird auf den fertigen Kacheln bei Zoom 16 (1 px = 1,58 m), und zwar
nur an der schwarzen Druckplatte: Strassen, Bahn, Gebaeude, Grenzen. Braune
Hoehenlinien und blaue Gewaesser wurden zwischen den Ausgaben neu gezeichnet
und wuerden nur stoeren.

Zwei Fallen, in die ich vorher gelaufen bin:

Phasenkorrelation taugt hier nicht. Die Weissung des Spektrums hebt gerade
die feinen Signaturunterschiede hervor, an denen sich die Kartengenerationen
unterscheiden -- zwischen Nachkriegsstich und moderner Ausgabe sprang sie
regelmaessig auf Fehlgipfel und lieferte je nach Ausschnitt Unsinn.
Gewoehnliche Kreuzkorrelation auf leicht weichgezeichneter Tinte fragt nach
der Lage einer Strasse statt nach der Strichfuehrung des Stechers und trifft.

Und der Bezug darf kein einzelnes Blatt sein. Das Mittel aus 1969, 1984 und
1995 laesst nur stehen, was ueber vier Jahrzehnte an derselben Stelle blieb.

Aufruf:  python nachpassung.py          nur messen
         python nachpassung.py -s       Korrekturen schreiben
"""
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from pmtiles.reader import MmapSource, Reader
from pyproj import Transformer
from scipy import ndimage

HIER = Path(__file__).parent
DATEN = HIER.parent / "public" / "data"
PASSPUNKTE = HIER / "passpunkte.json"

Z = 16
KANTE = 3                      # Feldgroesse in Kacheln
WEICH = 2.5                    # Weichzeichnung in Kachelpixeln
FX, FY = 8, 14                 # Suchraum, rund 13 bzw. 22 Meter
METER = 2 * math.pi * 6378137.0 / (2 ** Z * 256) * math.cos(math.radians(48.45))

BEZUG = ["1969", "1984", "1995"]
SCHWELLE = 8.0                 # ab hier lohnt die Nachpassung, in Metern

BREITEN = [48.407, 48.419, 48.431, 48.443, 48.455, 48.468, 48.480, 48.492]
LAENGEN = [11.848, 11.875, 11.902, 11.929, 11.956, 11.983]

nach_gk = Transformer.from_crs("EPSG:4326", "EPSG:31468", always_xy=True)


def kachel_xy(lon, lat):
    n = 2 ** Z
    return (int((lon + 180) / 360 * n),
            int((1 - math.log(math.tan(math.radians(lat))
                              + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n))


def flaeche(jahr, x0, y0):
    bild = Image.new("RGB", (256 * KANTE, 256 * KANTE), "white")
    with open(DATEN / f"{jahr}.pmtiles", "rb") as f:
        leser = Reader(MmapSource(f))
        for dx in range(KANTE):
            for dy in range(KANTE):
                roh = leser.get(Z, x0 + dx, y0 + dy)
                if roh is None:
                    continue
                bild.paste(Image.open(io.BytesIO(roh)).convert("RGB"),
                           (dx * 256, dy * 256))
    return np.asarray(bild).astype(np.float32)


def tinte(a):
    """Neutrales Schwarz, weich bewertet statt hart geschwellt."""
    hell, dunkel = a.max(axis=2), a.min(axis=2)
    return np.clip((190 - hell) / 120, 0, 1) * (hell - dunkel < 70)


def vorbereitet(a):
    a = ndimage.gaussian_filter(a, WEICH)
    a = a - a.mean()
    return a * (np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :])


def deckung(a, b):
    """Verschiebung des besten Zusammenfalls, nur im Fenster gesucht."""
    r = np.fft.ifft2(np.fft.fft2(a) * np.conj(np.fft.fft2(b))).real
    aus = np.vstack([np.hstack([r[:FY + 1, :FX + 1], r[:FY + 1, -FX:]]),
                     np.hstack([r[-FY:, :FX + 1], r[-FY:, -FX:]])])
    i, j = np.unravel_index(aus.argmax(), aus.shape)
    dy = i if i <= FY else i - aus.shape[0]
    dx = j if j <= FX else j - aus.shape[1]
    return dx, dy


def felder(jahre):
    """Schwarzplatte je Blatt und Feld, einmal eingelesen."""
    return {(j, lon, lat): tinte(flaeche(j, *kachel_xy(lon, lat)))
            for j in jahre for lat in BREITEN for lon in LAENGEN}


def messe(jahr, platten):
    """Noetige Verschiebung je Feld, in Gauss-Krueger-Metern.

    deckung liefert die Lage des Blattes minus die Lage des Bezugs. Positives
    dx heisst also zu weit oestlich, und die Korrektur zeigt nach Westen --
    daher das Minus. Bei dy heben sich zwei Umkehrungen auf: die Kachelzeile
    zaehlt nach Sueden, der Nordwert nach Norden, und positives dy heisst zu
    weit suedlich. Dieser Unterschied zwischen den Achsen ist die einzige
    Stelle, an der man sich hier verrechnen kann.
    """
    andere = [j for j in BEZUG if j != jahr]
    zeilen = []
    for lat in BREITEN:
        for lon in LAENGEN:
            a = platten[(jahr, lon, lat)]
            b = np.mean([platten[(j, lon, lat)] for j in andere], axis=0)
            if a.mean() < 0.02 or b.mean() < 0.02:
                continue
            dx, dy = deckung(vorbereitet(a), vorbereitet(b))
            E, N = nach_gk.transform(lon, lat)
            zeilen.append((E, N, -dx * METER, dy * METER))
    return np.array(zeilen, float)


def affin(E, N, klaffung, bezug, grenze=6.0):
    """Ausgleichsebene ueber das Blatt, mit Abweisung grober Ausreisser."""
    voll = np.column_stack([np.ones(len(E)), E - bezug[0], N - bezug[1]])
    dabei = np.ones(len(E), bool)
    for _ in range(3):
        p, *_ = np.linalg.lstsq(voll[dabei], klaffung[dabei], rcond=None)
        rest = voll @ p - klaffung
        neu = np.abs(rest) <= grenze
        if (neu == dabei).all():
            break
        dabei = neu
    s2 = (rest[dabei] ** 2).sum() / max(dabei.sum() - 3, 1)
    fehler = np.sqrt(s2 * np.diag(np.linalg.inv(voll[dabei].T @ voll[dabei])))
    return p, fehler, np.sqrt((rest[dabei] ** 2).mean()), dabei


def main():
    modelle = json.loads(PASSPUNKTE.read_text())
    jahre = list(modelle)
    platten = felder(jahre)
    ecken = [nach_gk.transform(lon, lat)
             for lon in (LAENGEN[0], LAENGEN[-1])
             for lat in (BREITEN[0], BREITEN[-1])]
    bezug = np.mean(ecken, axis=0)
    weit = np.array([[e - bezug[0], n - bezug[1]] for e, n in ecken])

    print("Klaffung des Kartenbilds gegen %s, Schwarzplatte bei z16"
          % "/".join(BEZUG))
    print("Blatt    Mitte O/N       Neigung O/N je km        Ecke    Rest")
    treffer = {}
    for jahr in jahre:
        d = messe(jahr, platten)
        po, fo, ro, mo = affin(d[:, 0], d[:, 1], d[:, 2], bezug)
        pn, fn, rn, mn = affin(d[:, 0], d[:, 1], d[:, 3], bezug)
        groesste = np.hypot(po[0] + weit @ po[1:], pn[0] + weit @ pn[1:]).max()
        alt = modelle[jahr].get("nachpassung")
        print("%s  %+5.1f/%+5.1f m  %+5.2f,%+5.2f / %+5.2f,%+5.2f m/km  %5.1f m  %.1f/%.1f m%s"
              % (jahr, po[0], pn[0], po[1] * 1000, po[2] * 1000,
                 pn[1] * 1000, pn[2] * 1000, groesste, ro, rn,
                 "   (bereits nachgepasst)" if alt else ""))
        if groesste > SCHWELLE and jahr not in BEZUG:
            # Gemessen wird auf den fertigen Kacheln, in denen eine frueher
            # gesetzte Nachpassung schon steckt. Was jetzt uebrigbleibt, kommt
            # also zu ihr hinzu, statt sie zu ersetzen -- sonst hobe der
            # zweite Lauf den ersten wieder auf.
            grund = np.array([alt["ost"], alt["nord"]]) if alt else np.zeros((2, 3))
            treffer[jahr] = {
                "ost": [round(float(v), 6) for v in grund[0] + po],
                "nord": [round(float(v), 6) for v in grund[1] + pn],
                "bezug": [round(float(v), 2) for v in bezug],
                "felder": int(mo.sum()),
                "rest_m": [round(float(ro), 2), round(float(rn), 2)],
                "quelle": "Schwarzplatte gegen " + "/".join(BEZUG),
            }

    print("\nUeber %.0f m und damit nachzupassen: %s"
          % (SCHWELLE, ", ".join(treffer) or "keines"))
    if "-s" not in sys.argv:
        print("(nur gemessen; mit -s schreiben)")
        return
    # Blaetter unter der Schwelle bleiben unangetastet: eine bestehende
    # Nachpassung wegzunehmen waere ein Eingriff, kein Messergebnis.
    for jahr, wert in treffer.items():
        modelle[jahr]["nachpassung"] = wert
    PASSPUNKTE.write_text(json.dumps(modelle, indent=1, ensure_ascii=False))
    print("passpunkte.json geschrieben -- betroffene Blaetter neu kacheln")


if __name__ == "__main__":
    main()
