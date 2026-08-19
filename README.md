# Moosburg historisch

**Acht Ausgaben derselben Karte, deckungsgleich übereinandergelegt.** Die
Topographische Karte 1:25 000, Blatt 7537 Moosburg a.d.Isar, von 1960 bis 2008
— dazu die Gegenwart. Eine Zeitschiene mit echten Jahresabständen blendet von
Ausgabe zu Ausgabe, und die Stadt wächst unter dem Schieber. Mobile-first,
rein statisch, ohne Tracking.

🔗 **Live:** [bagruber.github.io/moosburghistorisch](https://bagruber.github.io/moosburghistorisch/)
· auch unter [moosburg.eu/data/historisch/](https://moosburg.eu/data/historisch/)

> ⚠️ **Hinweis:** Dieses Projekt ist eine **private Eigenentwicklung**, kein
> offizielles Angebot einer Behörde. Wünsche und Bug-Reports gerne als
> [GitHub-Issue](https://github.com/bagruber/moosburghistorisch/issues).
> Keine Datenerfassung, kein Tracking, keine Cookies.

## Die Karten

Archivscans der Topographischen Karte 1:25 000, Blatt 7537, aus der
Historischen Sammlung des Topographischen Archivs der Bayerischen
Vermessungsverwaltung: **1960, 1963, 1969, 1984, 1992, 1995, 2001, 2008**.
Jedes Blatt deckt dieselbe Fläche ab — 11°50′ bis 12°00′ östlicher Länge,
48°24′ bis 48°30′ nördlicher Breite, gut 12 × 11 Kilometer.

Die Gegenwart kommt von außen: [TopPlusOpen](https://gdz.bkg.bund.de) des
Bundesamts für Kartographie und Geodäsie. Bewusst eine topographische Karte
und kein Luftbild — gleiches Register wie die alten Blätter, dadurch der
ehrlichste Vergleich.

## Wie sie passgenau werden

Nicht über den Blattrahmen, sondern über das **Kilometergitter**, das jedes
Blatt am Rand trägt: Gauß-Krüger Zone 4 auf glatten Kilometerwerten. Aus den
Gitterstrichen entsteht je Blatt eine Affinabbildung vom Scan in die
Landeskoordinaten. Die Restklaffung bleibt unter drei Metern — Papierverzug
spielt bei diesen Blättern also keine Rolle.

Der eigentliche Stolperstein liegt woanders: Die gedruckten Gradangaben der
alten Blätter stehen auf dem **Bessel-Datum**. Wer sie für heutige Koordinaten
nimmt, legt die Karte rund 150 Meter daneben — deutlich sichtbar, sobald zwei
Jahrgänge übereinanderliegen.

## Stack

Bewusst minimal — läuft rein statisch auf GitHub Pages.

- **[Vite](https://vite.dev) 6** + **React 19** + **TypeScript**
- **[Tailwind CSS v4](https://tailwindcss.com)** via `@tailwindcss/vite`
- **[MapLibre GL JS](https://maplibre.org)** + **[PMTiles](https://protomaps.com/docs/pmtiles)**
  — je Jahrgang eine Kacheldatei im Repo, gelesen per HTTP-Range-Requests,
  ganz ohne Tile-Server
- **Python** (numpy, pyproj, scipy, Pillow, pmtiles) für die Pipeline (`etl/`)

## Lokal entwickeln

```bash
npm install
npm run dev        # Dev-Server auf http://localhost:5173
npm run build      # Produktions-Build nach dist/
npm run typecheck  # nur tsc, kein Build
npm run data       # Georeferenzierung und Kacheln neu erzeugen
```

Die Pipeline erwartet die Scans in `etl/scans/`. Sie kommen verlustfrei aus
den PDFs:

```bash
for f in *.pdf; do pdfimages -j "$f" "etl/scans/${f%.pdf}"; done
```

`etl/georef.py` schreibt `etl/passpunkte.json` — je Blatt die beiden
Achsfits, die Restklaffungen und das gerechnete Kartenfeld samt Sollvergleich.
Wer eine Zuordnung von Hand korrigieren will, ändert dort die Koeffizienten;
`etl/kacheln.py` liest ausschließlich diese Datei.

## Deployment

Zwei Ziele, zwei Pfade, ein Branch:

- **GitHub Pages** — `.github/workflows/deploy.yml`, Basis `/moosburghistorisch/`
- **moosburg.eu** — `.github/workflows/hostinger.yml`, Basis `/data/historisch/`:
  dort hängen die Karten als Unterpunkt am [Data Hub](https://moosburg.eu/data/),
  neben der Baumkarte.

`public/.htaccess` schaltet die gzip-Komprimierung für `.pmtiles` ab — sie
würde die Byte-Offsets verschieben und die Karte leer lassen, ohne
Fehlermeldung.

## Ausblick

- Ältere Blätter: Urpositionsblätter (1817–1841) und Uraufnahme (1808–1864)
- Luftbild als zweite Gegenwart
- Vorhang-Vergleich mit ziehbarer Trennlinie statt nur Überblendung
- Die Zeichenerklärungen der Jahrgänge, die beim Beschnitt wegfallen

## Geschwister-Apps

Teil einer kleinen Familie von Daten-Anwendungen für Moosburg:

- **[bagruber/baumkarte](https://github.com/bagruber/baumkarte)** — Einzelbäume auf der Karte
- **[bagruber/haushaltvis](https://github.com/bagruber/haushaltvis)** — Haushaltsvisualisierung
- **[bagruber/datahub](https://github.com/bagruber/datahub)** — Daten-Dashboards
- **[bagruber/council](https://github.com/bagruber/council)** — Stadtrats-Transparenz
- **bagruber/moosburghistorisch** *(dieses Repo)* — historische Karten

## Verantwortung

Entwickelt und betrieben von **Benedict Arya Gruber**. Private
Eigenentwicklung — kein offizielles Produkt einer Verwaltung.

Kartengrundlage: Bayerische Vermessungsverwaltung. Gegenwart: TopPlusOpen,
© Bundesamt für Kartographie und Geodäsie.

Kontakt: [benedict.gruber@fresh.bayern](mailto:benedict.gruber@fresh.bayern) ·
[gruber.am](https://www.gruber.am)

Lizenz: MIT (Code). Die Kartenblätter selbst stehen unter den Bedingungen der
Bayerischen Vermessungsverwaltung.
