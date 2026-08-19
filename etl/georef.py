"""Georeferenzierung der TK25-Blaetter 7537 ueber ihr Kilometergitter.

Jedes Blatt traegt am Rand die Striche des Gauss-Krueger-Gitters (Zone 4,
Bessel/Potsdam) auf glatten Kilometerwerten. Sie sind auf jedem Blatt kraeftig
gedruckt, waehrend der Blattrahmen auf mehreren Scans zu blass fuer eine
Profilsuche ist -- deshalb ist das Gitter und nicht der Rahmen die Grundlage.

Aus den Strichen entsteht eine Affinabbildung Pixel -> Gauss-Krueger. Sie ist
im Ansatz exakt: das Papier ist eine massstaebliche Kopie der GK-Ebene, der
Scanner fuegt nur Skalierung, Scherung und Drehung hinzu. Was als Restklaffung
uebrig bleibt, ist Papierverzug -- gemessen bleibt er unter 3 m.

Zwei Eigenheiten des Bestands stecken im Code:

* Die Faltkarten von 2001 und 2008 tragen zwei Kilometergitter uebereinander.
  Die Farbe hilft beim Trennen nicht -- bis 1995 ist Gauss-Krueger schwarz, auf
  den Faltkarten ist es blau und das schwarze Gitter das UTM-Netz. Getrennt
  wird geometrisch: das UTM-Netz steht gut zwei Grad schief zum Blattschnitt,
  seine Striche treffen die gegenueberliegenden Blattraender rund 200 px
  versetzt, das Gauss-Krueger-Gitter laeuft dem Rahmen entlang.
* Auf dem Blatt von 2008 ist das Gauss-Krueger-Gitter nur an je einem Rand
  angerissen. Aus einer einzelnen Strichreihe laesst sich die Blattdrehung
  nicht ablesen; sie kommt dann aus der bekannten Schraege des UTM-Netzes.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import Transformer

Image.MAX_IMAGE_PIXELS = None
HIER = Path(__file__).parent

# Blatt 7537: Kartenfeld nach Blattschnitt der TK25, Grad auf Bessel/Potsdam
WEST, OST = 11 + 50 / 60, 12.0
SUED, NORD = 48.4, 48.5
# Gitterlinien im Kartenfeld (Kilometerwerte, GK Zone 4)
OSTWERTE = np.arange(4488, 4501) * 1000.0
NORDWERTE = np.arange(5363, 5374) * 1000.0

PX_PRO_KM = (1000_000 / 25000) * 300 / 25.4   # 1 km, 1:25000, 300 dpi -> 472,4 px

zu_gk = Transformer.from_crs("EPSG:4314", "EPSG:31468", always_xy=True)


def gk_gegen_utm(E=4493840.0, N=5367920.0):
    """Winkel zwischen Gauss-Krueger-Gitternord und UTM-Gitternord, Blattmitte."""
    nach_utm = Transformer.from_crs("EPSG:31468", "EPSG:25832", always_xy=True)
    x0, y0 = nach_utm.transform(E, N)
    x1, y1 = nach_utm.transform(E, N + 1000.0)
    return np.arctan2(x1 - x0, y1 - y0)


GK_GEGEN_UTM = gk_gegen_utm()          # rund -2,25 Grad


def rahmen_soll():
    """Kartenfeldecken in GK und die erwartete Blattgroesse in Pixeln."""
    ecken = {k: zu_gk.transform(lon, lat) for k, (lon, lat) in {
        "nw": (WEST, NORD), "no": (OST, NORD),
        "sw": (WEST, SUED), "so": (OST, SUED)}.items()}
    breite = (ecken["no"][0] - ecken["nw"][0] + ecken["so"][0] - ecken["sw"][0]) / 2
    hoehe = (ecken["nw"][1] - ecken["sw"][1] + ecken["no"][1] - ecken["so"][1]) / 2
    return ecken, breite / 1000 * PX_PRO_KM, hoehe / 1000 * PX_PRO_KM


def farbmaske(bild):
    """Grauwert und Maske kraeftiger Druckfarbe."""
    a = np.asarray(bild.convert("RGB")).astype(np.int16)
    return np.asarray(bild.convert("L")), a.min(axis=2) < 110


def segmente(zeile, maxbreite=12, freiraum=25):
    """Mittelpunkte freistehender schmaler Farbsegmente einer Bildzeile.

    Der Freiraum ist das eigentliche Sieb: ein Gitterstrich steht allein im
    weissen Randfeld, waehrend Schrift und Kartenzeichen immer Nachbarn in
    wenigen Pixeln Abstand haben.
    """
    idx = np.nonzero(zeile)[0]
    if idx.size == 0:
        return np.empty(0)
    bruch = np.nonzero(np.diff(idx) > 1)[0]
    links = idx[np.concatenate([[0], bruch + 1])]
    rechts = idx[np.concatenate([bruch, [idx.size - 1]])]
    luecke = links[1:] - rechts[:-1]
    frei_links = np.concatenate([[freiraum + 1], luecke])
    frei_rechts = np.concatenate([luecke, [freiraum + 1]])
    ok = ((rechts - links + 1 <= maxbreite)
          & (frei_links > freiraum) & (frei_rechts > freiraum))
    return (links[ok] + rechts[ok]) / 2


def gitterzeile(x, dlo=468.0, dhi=477.0):
    """Passt ein Kilometerraster in die Segmentmitten einer Zeile.

    Entscheidend ist nicht die blosse Trefferzahl, sondern dass die Raster-
    indizes lueckenarm aufeinanderfolgen: Kartenzeichen treffen zufaellig,
    aber nie regelmaessig ueber die ganze Blattbreite.
    """
    if x.size < 8:
        return 0, 0.0, np.empty(0)
    best = (0, 0.0, np.empty(0))
    for d in np.arange(dlo, dhi, 0.5):
        h, kanten = np.histogram(np.mod(x, d), bins=np.arange(0, d + 6, 6))
        phase = kanten[h.argmax()] + 3
        k = np.round((x - phase) / d)
        treffer = np.abs(x - phase - k * d) < 7
        if treffer.sum() < 8:
            continue
        ki = np.unique(k[treffer])
        if ki.size < 8 or ki.max() - ki.min() > ki.size + 2:
            continue
        if ki.size > best[0]:
            best = (int(ki.size), float(np.mod(x[treffer][0], d)), x[treffer])
    return best


def kandidatenbaender(maske, schritt=3):
    """Alle Zeilengruppen, in denen ein Kilometerraster steckt.

    Getrennt wird nicht nur nach Zeilennaehe, sondern auch nach Rasterphase:
    auf den Faltkarten liegen die Striche zweier Gitter wenige Millimeter
    uebereinander im selben Randfeld.
    """
    treffer = []
    for y in range(0, maske.shape[0], schritt):
        n, phase, xs = gitterzeile(segmente(maske[y]))
        if n >= 9 and xs.size and xs.max() - xs.min() > 3500:
            treffer.append((y, phase, xs))
    gruppen = []
    for t in treffer:
        vor = gruppen[-1][-1] if gruppen else None
        versatz = abs(t[1] - vor[1]) if vor else 0.0
        if vor and t[0] - vor[0] <= 60 and min(versatz, 472 - versatz) < 20:
            gruppen[-1].append(t)
        else:
            gruppen.append([t])
    return [g for g in gruppen if len(g) >= 2]


def striche(grau, gruppe):
    """Subpixel-Lage der Gitterstriche eines Bandes.

    Gewichtet wird mit der Schwaerze, gemittelt ueber die Zeilen, in denen das
    Raster erkannt wurde. Liefert (Positionen quer, mittlere Zeile).
    """
    zeilen = [t[0] for t in gruppe]
    y0, y1 = min(zeilen), max(zeilen) + 3
    roh = np.sort(np.concatenate([t[2] for t in gruppe]))
    cluster, akt = [], [roh[0]]
    for v in roh[1:]:
        if v - akt[-1] < 40:
            akt.append(v)
        else:
            cluster.append(akt)
            akt = [v]
    cluster.append(akt)
    streifen = 255.0 - grau[y0:y1].astype(np.float64)
    streifen[streifen < 60] = 0.0
    lage = []
    for c in cluster:
        m = int(round(np.median(c)))
        von = max(0, m - 7)
        fenster = streifen[:, von:m + 8].sum(axis=0)
        if fenster.sum() > 0:
            xs = np.arange(von, von + fenster.size)
            lage.append(float((fenster * xs).sum() / fenster.sum()))
    return np.array(lage), (y0 + y1) / 2


def waehle_baender(funde, sollzahl, soll_abstand):
    """Die Baender des Gauss-Krueger-Gitters auswaehlen.

    Erste Wahl ist ein Paar gegenueberliegender Raender, dessen Striche sich
    quer kaum versetzen -- das schliesst das schraege UTM-Netz aus. Gibt es
    kein solches Paar, bleibt das einzelne Band, das genau so viele Striche
    zeigt, wie der Blattschnitt Gitterlinien zulaesst.
    """
    def versatz(a, b):
        return float(np.median(np.abs(a[:, None] - b[None, :]).min(axis=1)))

    bestes = None
    for i, (li, mi) in enumerate(funde):
        for j, (lj, mj) in enumerate(funde):
            if abs((mj - mi) - soll_abstand) > 170 or li.size < 9 or lj.size < 9:
                continue
            quer = versatz(li, lj)
            if quer < 60 and (bestes is None or quer < bestes[0]):
                bestes = (quer, [i, j])
    if bestes:
        return bestes[1]
    spanne = (sollzahl - 1) * PX_PRO_KM
    voll = [k for k, (lage, _) in enumerate(funde)
            if lage.size == sollzahl and abs(lage.max() - lage.min() - spanne) < 30]
    return [max(voll, key=lambda k: funde[k][0].size)] if voll else []


def zuordnungen(funde, gewaehlt, kandidaten):
    """Alle plausiblen Kilometerzuordnungen einer Achse.

    Ein einzelner Streufund am Blattrand -- eine Falzkante, eine Rahmenlinie --
    setzt sich fast lueckenlos ins Raster und verschiebt sonst das ganze Blatt
    um einen Kilometer. Deshalb wird nicht entschieden, sondern aufgezaehlt:
    jede Verschiebung, die ins Kartenfeld passt, und dazu die Faelle, in denen
    der erste oder letzte Strich zu verwerfen ist. Welche Variante stimmt,
    sagt spaeter die Randprobe.
    """
    anker = max(gewaehlt, key=lambda k: funde[k][0].size)
    voll = funde[anker][0]
    aus = []
    for reihe in ([voll, voll[1:], voll[:-1]] if voll.size > 3 else [voll]):
        stufen = np.round((reihe - reihe[0]) / PX_PRO_KM).astype(int)
        if stufen[-1] >= len(kandidaten):
            continue
        for schub in range(len(kandidaten) - int(stufen[-1])):
            werte = kandidaten[stufen + schub]
            satz = []
            for k in gewaehlt:
                lage, quermitte = funde[k]
                treffer = np.abs(lage[:, None] - reihe[None, :]).argmin(axis=1)
                nah = np.abs(lage - reihe[treffer]) < 60
                satz.append((lage[nah], quermitte, werte[treffer[nah]]))
            aus.append(satz)
    return aus


def tinte(maske, punkte):
    u = np.rint(punkte[:, 0]).astype(int)
    v = np.rint(punkte[:, 1]).astype(int)
    drin = (u >= 0) & (v >= 0) & (u < maske.shape[1]) & (v < maske.shape[0])
    return float(maske[v[drin], u[drin]].mean()) if drin.any() else 0.0


def randprobe(maske, px):
    """Tintenkontrast am vorhergesagten Blattrand.

    Innerhalb des Kartenfelds steht Karte, ausserhalb weisses Papier. Diese
    Stufe entscheidet zwischen den Kilometerzuordnungen: eine falsche legt den
    Rahmen um 472 px versetzt mitten ins Kartenbild, und der Kontrast bricht
    zusammen.
    """
    mitte = (np.array(px["nw"]) + np.array(px["so"])) / 2
    werte = []
    for a, b in (("nw", "no"), ("no", "so"), ("so", "sw"), ("sw", "nw")):
        p0, p1 = np.array(px[a]), np.array(px[b])
        lauf = p0 + (p1 - p0) * np.linspace(0.08, 0.92, 100)[:, None]
        quer = np.array([-(p1 - p0)[1], (p1 - p0)[0]])
        quer = quer / np.linalg.norm(quer)
        if quer @ (mitte - p0) > 0:
            quer = -quer
        for tiefe in (20, 35, 50):
            werte.append(tinte(maske, lauf - quer * tiefe)
                         - tinte(maske, lauf + quer * tiefe))
    return float(np.mean(werte))


def passe_an(u, v, ziel):
    """Kleinste Quadrate fuer ziel = a*u + b*v + c."""
    A = np.column_stack([u, v, np.ones_like(u)])
    loesung, *_ = np.linalg.lstsq(A, ziel, rcond=None)
    return loesung, A @ loesung - ziel


def langstriche(farbe, mindest=25):
    """Maske der Pixel in einem langen senkrechten Farblauf.

    Nur fuer die Suche nach dem UTM-Netz gebraucht: dessen Linien laufen quer
    durchs Kartenbild, wo kein Merkmal freisteht und das Sieb aus segmente()
    nicht greift.
    """
    H, W = farbe.shape
    p = np.zeros((H + 2, W), bool)
    p[1:-1] = farbe
    sx, sy = np.nonzero((p[1:-1] & ~p[:-2]).T)
    _, ey = np.nonzero((p[1:-1] & ~p[2:]).T)
    lang = (ey - sy + 1) >= mindest
    maske = np.zeros((W, H), bool)
    for x, y0, y1 in zip(sx[lang], sy[lang], ey[lang]):
        maske[x, y0:y1 + 1] = True
    return maske.T


def schraeges_netz(grau, farbe, mindestschraege=0.02):
    """Pixelschraege der UTM-Gitterlinien, gemessen zwischen weit
    auseinanderliegenden Baendern."""
    funde = [striche(grau, g) for g in kandidatenbaender(langstriche(farbe))]
    werte = []
    for i, (li, mi) in enumerate(funde):
        for j, (lj, mj) in enumerate(funde):
            if mj - mi < 2500 or li.size < 9 or lj.size < 9:
                continue
            treffer = np.abs(lj[:, None] - li[None, :]).argmin(axis=1)
            nah = np.abs(lj - li[treffer]) < 300
            if nah.sum() >= 8:
                werte.append(np.mean(lj[nah] - li[treffer][nah]) / (mj - mi))
    werte = np.array([w for w in werte if abs(w) > mindestschraege])
    return float(np.median(werte)) if werte.size else None


def drehung_aus_utm(schraege):
    """Blattdrehung aus der Schraege des UTM-Netzes.

    Zwischen Gauss-Krueger-Gitternord und UTM-Gitternord liegt auf diesem
    Blatt ein fester, rechenbarer Winkel. Wer den einen misst, kennt den
    anderen -- und damit die Drehung des Blattes auf dem Scanner. Am Blatt
    2001, wo beide Gitter vollstaendig sind, stimmt der so bestimmte Wert bis
    auf 0,003 Grad mit dem aus dem Gitter gerechneten ueberein.
    """
    return -np.arctan(np.tan(np.arctan(schraege) - GK_GEGEN_UTM))


def fasse(teile):
    (aE, rE), (aN, rN) = teile["E"], teile["N"]
    return dict(ostachse=list(map(float, aE)), nordachse=list(map(float, aN)),
                klaffung=dict(ost_rms=float(np.sqrt((rE ** 2).mean())),
                              ost_max=float(np.abs(rE).max()),
                              nord_rms=float(np.sqrt((rN ** 2).mean())),
                              nord_max=float(np.abs(rN).max())))


def feldecken(modell, gk_ecken):
    """Die vier Kartenfeldecken in Pixeln."""
    A = np.array([modell["ostachse"][:2], modell["nordachse"][:2]])
    b = np.array([modell["ostachse"][2], modell["nordachse"][2]])
    Ai = np.linalg.inv(A)
    return {k: Ai @ (np.array(gk_ecken[k]) - b) for k in gk_ecken}


def mit_drehung(u, v, ziel, dreh, achse):
    """Achsfit bei vorgegebener Blattdrehung."""
    if achse == "E":
        A = np.column_stack([u * np.cos(dreh) + v * np.sin(dreh), np.ones_like(u)])
        lsg, *_ = np.linalg.lstsq(A, ziel, rcond=None)
        koeff = np.array([lsg[0] * np.cos(dreh), lsg[0] * np.sin(dreh), lsg[1]])
    else:
        A = np.column_stack([u * np.sin(dreh) - v * np.cos(dreh), np.ones_like(u)])
        lsg, *_ = np.linalg.lstsq(A, ziel, rcond=None)
        koeff = np.array([lsg[0] * np.sin(dreh), -lsg[0] * np.cos(dreh), lsg[1]])
    return koeff, A @ lsg - ziel


def rahmenkanten(ink, soll, tol=45):
    """Die beiden Rahmenlinien einer Achse, sofern eindeutig.

    Der Rahmen ist der Blattschnitt selbst, also eine unabhaengige Aussage
    ueber die Lage des Kartenfelds -- und damit die Probe auf das Gitter. Er
    ist nur auf einem Teil der Blaetter kraeftig genug; wo er fehlt, bleibt
    es beim Gitter allein.
    """
    W = ink.shape[1]
    anteil = ink[:, int(W * 0.35):int(W * 0.65)].mean(axis=1)
    gruppen = []
    for i in np.nonzero(anteil > 0.85)[0]:
        if gruppen and i - gruppen[-1][-1] <= 4:
            gruppen[-1].append(i)
        else:
            gruppen.append([i])
    linien = [float(np.mean(g)) for g in gruppen]
    paare = [(a, b) for a in linien for b in linien if abs((b - a) - soll) < tol]
    if not paare:
        return None
    return min(paare, key=lambda p: abs((p[1] - p[0]) - soll)), W * 0.5


def loese(punkte, einzeln, dreh):
    """Beide Achsfits; fuer Achsen mit nur einem Randband mit fester Drehung."""
    teile = {}
    for achse in ("E", "N"):
        u, v, ziel = punkte[achse][:, 0], punkte[achse][:, 1], punkte[achse][:, 2]
        teile[achse] = (mit_drehung(u, v, ziel, dreh, achse) if achse in einzeln
                        else passe_an(u, v, ziel))
    return fasse(teile)


def blatt(pfad):
    grau, farbe = farbmaske(Image.open(pfad))
    ecken, soll_b, soll_h = rahmen_soll()

    saetze, einzeln = {}, []
    for achse, maske, bild, kandidaten, soll in (
            ("E", farbe, grau, OSTWERTE, soll_h + 46),
            ("N", farbe.T, grau.T, NORDWERTE[::-1], soll_b + 46)):
        funde = [striche(bild, g) for g in kandidatenbaender(maske)]
        gewaehlt = waehle_baender(funde, len(kandidaten), soll)
        if not gewaehlt:
            raise SystemExit(f"{pfad.name}: {achse}-Gitter nicht gefunden")
        if len(gewaehlt) < 2:
            einzeln.append(achse)
        saetze[achse] = [
            np.array([(x, quermitte, w) if achse == "E" else (quermitte, x, w)
                      for lage, quermitte, werte in satz
                      for x, w in zip(lage, werte)], float)
            for satz in zuordnungen(funde, gewaehlt, kandidaten)]

    dreh = 0.0
    if einzeln:
        schraege = schraeges_netz(grau, farbe)
        if schraege is None:
            raise SystemExit(f"{pfad.name}: nur ein Randband je Achse und kein "
                             "UTM-Netz -- Blattdrehung unbestimmt")
        dreh = drehung_aus_utm(schraege)

    bestes = None
    for satz_ost in saetze["E"]:
        for satz_nord in saetze["N"]:
            modell = loese({"E": satz_ost, "N": satz_nord}, einzeln, dreh)
            px = feldecken(modell, ecken)
            breite = (px["no"][0] - px["nw"][0] + px["so"][0] - px["sw"][0]) / 2
            hoehe = (px["sw"][1] - px["nw"][1] + px["so"][1] - px["no"][1]) / 2
            if abs(breite - soll_b) > 60 or abs(hoehe - soll_h) > 60:
                continue
            guete = (round(randprobe(farbe, px), 3), len(satz_ost) + len(satz_nord))
            if bestes is None or guete > bestes[0]:
                bestes = (guete, modell, satz_ost, satz_nord)
    if bestes is None:
        raise SystemExit(f"{pfad.name}: keine stimmige Kilometerzuordnung")

    guete, modell, satz_ost, satz_nord = bestes

    # Probe am Blattrahmen: der Rahmen ist der Blattschnitt selbst und damit
    # eine vom Gitter unabhaengige Aussage. Sie hat einen Fehler gefunden, den
    # die Klaffungen nicht zeigen konnten -- auf dem Blatt 2008 stammte das
    # einzige Nordband nicht vom Gauss-Krueger-Gitter, sondern von den
    # UTM-Linien im Kartenbild. Der Fit war in sich stimmig und lag trotzdem
    # 146 m daneben. Weicht das Modell vom Rahmen ab, gilt der Rahmen.
    px = feldecken(modell, ecken)
    kanten = rahmenkanten(farbe, soll_h)
    abweichung = None
    if kanten:
        (oben, unten), spalte = kanten
        abweichung = round(max(abs((px["nw"][1] + px["no"][1]) / 2 - oben),
                               abs((px["sw"][1] + px["so"][1]) / 2 - unten)), 1)
        if abweichung > 15:
            if not einzeln:
                dreh = np.arctan2(modell["ostachse"][1], modell["ostachse"][0])
            satz_nord = np.array(
                [(spalte, oben, (ecken["nw"][1] + ecken["no"][1]) / 2),
                 (spalte, unten, (ecken["sw"][1] + ecken["so"][1]) / 2)], float)
            # Die Ostachse behaelt ihre Sonderbehandlung: haengt sie an einem
            # einzigen Randband, waere ein freier Fit unterbestimmt.
            modell = loese({"E": satz_ost, "N": satz_nord},
                           sorted({*einzeln, "N"}), dreh)
            px = feldecken(modell, ecken)

    breite = (px["no"][0] - px["nw"][0] + px["so"][0] - px["sw"][0]) / 2
    hoehe = (px["sw"][1] - px["nw"][1] + px["so"][1] - px["no"][1]) / 2
    modell.update(
        datei=pfad.name, groesse=[int(grau.shape[1]), int(grau.shape[0])],
        striche=dict(ost=len(satz_ost), nord=len(satz_nord)),
        drehung=float(np.degrees(dreh)) if einzeln else None,
        randprobe=guete[0], rahmenabweichung=abweichung,
        kartenfeld={k: [round(float(v[0]), 1), round(float(v[1]), 1)]
                    for k, v in px.items()},
        probe=dict(breite_px=round(breite, 1), soll_breite=round(soll_b, 1),
                   hoehe_px=round(hoehe, 1), soll_hoehe=round(soll_h, 1)))
    return modell


def main():
    aus = {}
    for pfad in sorted((HIER / "scans").glob("*.jpg")):
        try:
            m = blatt(pfad)
        except SystemExit as fehler:
            print("%-26s %s" % (pfad.name, fehler))
            continue
        aus[pfad.name.split("_")[3][:4]] = m
        k, p = m["klaffung"], m["probe"]
        rand = m["rahmenabweichung"]
        print("%-26s Striche %2d/%2d  Klaffung E %4.1f/%4.1f m  N %4.1f/%4.1f m"
              "  Feld %.0fx%.0f px (soll %.0fx%.0f)  Rahmen %s%s"
              % (pfad.name, m["striche"]["ost"], m["striche"]["nord"],
                 k["ost_rms"], k["ost_max"], k["nord_rms"], k["nord_max"],
                 p["breite_px"], p["hoehe_px"], p["soll_breite"], p["soll_hoehe"],
                 "nicht lesbar" if rand is None else "%+.0f px" % rand,
                 "" if m["drehung"] is None
                 else "  Drehung aus UTM-Netz %+.3f Grad" % m["drehung"]))
    (HIER / "passpunkte.json").write_text(
        json.dumps(aus, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
