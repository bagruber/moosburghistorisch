# Moosburg historisch — Projektkontext

*Lebendes Arbeitsdokument. Vollständig lesen, bevor Code geschrieben wird.
Änderungen mit Datum vermerken. Stand: 19.08.2026*

---

## 0. Arbeitsweise (Karpathy-Prinzipien)

Nicht verhandelbar, gelten für jede Änderung:

1. **Think Before Coding** — Annahmen explizit machen. Bei Mehrdeutigkeit
   Alternativen zeigen und nachfragen, nicht raten.
2. **Simplicity First** — Einfachste lauffähige Lösung. Keine spekulativen
   Features, keine Abstraktionen für Einmal-Nutzung.
3. **Surgical Changes** — Nur ändern, was die Aufgabe verlangt. Bestehenden
   Stil matchen, nicht „nebenbei verbessern".
4. **Goal-Driven Execution** — Vage Aufgaben in messbare Erfolgskriterien
   übersetzen, mehrstufige Arbeit mit Checkpoints strukturieren.

**Weitere Regeln:**
- Keine Erwähnung von KI-Tools/Assistenten — nirgendwo: nicht im Code, nicht
  in Commits, nicht im README, nicht in der App.
- Sprache: UI-Texte und Doku deutsch, Code-Bezeichner deutsch oder englisch,
  aber innerhalb einer Datei einheitlich.
- Kein Tracking, keine Cookies, kein `localStorage`/`sessionStorage`.

---

## 1. Projektziel

Acht Ausgaben derselben topographischen Karte deckungsgleich übereinander-
legen und über eine Zeitschiene durchblättern. Statische Webapp, mobile-first,
Hosting auf GitHub Pages (`bagruber.github.io/moosburghistorisch/`) und
parallel auf `moosburg.eu/data/historisch/` neben der Baumkarte.

Teil der Familie unter `bagruber/*` (moosburg, datahub, haushaltvis, council,
baumkarte) — gleiche Designsprache, gleicher Stack.

---

## 2. Datenlage

### Der Bestand

Acht PDFs im Repo-Wurzelverzeichnis, alle **dasselbe Blatt**: TK25 Blatt 7537
„Moosburg a.d.Isar". Jedes PDF enthält genau ein eingebettetes JPEG, 300 dpi,
RGB — kein Vektor. Mit `pdfimages -j` verlustfrei herauszuholen (kein
Neukodieren), Ablage in `etl/scans/`, nicht im Git.

| Jahrgänge | Bild | Layout |
|---|---|---|
| 1960, 1963, 1969, 1984, 1992, 1995 | 7320 × 7086 px | ganzes Blatt hochkant, Zeichenerklärung rechts |
| 2001, 2008 | 9448 × 5905 px | Faltkarten-Scan, Umschlag und Legende links |

**Blattschnitt** (für alle gleich): 11°50′–12°00′ östliche Länge,
48°24′–48°30′ nördliche Breite, **auf Bessel/Potsdam**. Das sind 12,32 × 11,12 km,
im Maßstab 1:25 000 bei 300 dpi also **5824 × 5253 px** — dieser Sollwert ist
die wichtigste Probe der ganzen Pipeline, weil er unabhängig gerechnet ist.

### 300 dpi heißt 2,12 m am Boden

Daraus folgt die maximale Zoomstufe: z16 liefert 1,58 m/px, z15 nur 3,17 m/px.
z16 überabtastet leicht (Faktor 1,34), z15 wäre zu grob für die Schrift. Also
z16 als Maximum, darüber Overzoom im Betrachter.

### Der Datumsversatz — 150 Meter

Die alten Blätter tragen als Eckwert `48°30′ / 11°50′`. Das Blatt von 2008
nennt an derselben physischen Ecke `48°29′56,6″ / 11°49′54,9″`. Der Unterschied
ist der Übergang Bessel/Potsdam → ETRS89: **rund 105 m nach Süden, 105 m nach
Osten, zusammen etwa 150 m.** Wer die gedruckten Gradangaben für WGS84 nimmt,
legt das Blatt um 75 Pixel bei z16 daneben.

`pyproj` erledigt den Übergang zuverlässig: EPSG:4314 → EPSG:4326 reproduziert
den gedruckten Wert auf 0,1 Bogensekunde genau (≈ 3 m). Kein NTv2-Gitter nötig.

---

## 3. Georeferenzierung (`etl/georef.py`)

**Grundlage ist das Kilometergitter, nicht der Blattrahmen.** Der Rahmen ist
auf mehreren Scans zu blass für eine Profilsuche; die Gitterstriche am
Blattrand sind überall kräftig und liegen auf glatten Kilometerwerten
(Gauß-Krüger Zone 4, EPSG:31468).

Aus den Strichen entsteht eine **Affinabbildung Pixel → Gauß-Krüger**, je
Achse ein Fit mit drei Parametern. Das ist im Ansatz exakt: Papier ist eine
maßstäbliche Kopie der GK-Ebene, der Scanner fügt nur Skalierung, Scherung und
Drehung hinzu. Was als Restklaffung übrigbleibt, ist Papierverzug.

### Ergebnis (19.08.2026)

| Blatt | Striche E/N | Klaffung E rms/max | N rms/max | Feld px |
|---|---|---|---|---|
| 1960 | 26/22 | 2,1 / 4,0 m | 1,2 / 2,3 m | 5819 × 5273 |
| 1963 | 24/22 | 2,4 / 5,8 m | 1,0 / 3,3 m | 5815 × 5257 |
| 1969 | 26/22 | 2,4 / 4,8 m | 1,3 / 2,3 m | 5816 × 5266 |
| 1984 | 24/22 | 2,1 / 3,8 m | 1,3 / 3,1 m | 5807 × 5246 |
| 1992 | 26/20 | 2,8 / 5,9 m | 1,4 / 3,4 m | 5807 × 5245 |
| 1995 | 26/22 | 2,3 / 5,2 m | 1,5 / 2,9 m | 5802 × 5231 |
| 2001 | 24/22 | 2,1 / 5,4 m | 0,7 / 1,5 m | 5814 × 5256 |
| 2008 | 12/2 | 1,5 / 2,4 m | Rahmen | 5824 × 5260 |

Sollwert 5824 × 5253 px. **Papierverzug ist damit vom Tisch** — eine
Affinabbildung genügt, ein Passpunktnetz über die Fläche wäre Aufwand ohne
Gewinn.

Nebenbefund: Die Blätter sind auf dem Scanner in x und y **unterschiedlich
skaliert**, bis zu 0,46 %. Eine Ähnlichkeitsabbildung wäre also zu wenig, die
Affinabbildung fängt es auf. Die **Drehung** dagegen stimmt auf beiden Achsen
bis auf 0,03° überein — der Scan hat keine messbare Scherung. Das ist der
Grund, warum eine Achse mit nur einem Randband ihre Richtung von der anderen
übernehmen darf.

### Vier Fallen, die im Code stecken

**Zwei Kilometergitter auf den Faltkarten.** 2001 und 2008 tragen neben dem
Gauß-Krüger-Gitter ein UTM-Gitter mit demselben Kilometerabstand. Die Farbe
hilft beim Trennen **nicht**: bis 1995 ist Gauß-Krüger schwarz, auf den
Faltkarten ist es *blau* und das schwarze Gitter das UTM-Netz. Getrennt wird
geometrisch — das UTM-Netz steht gut zwei Grad schief zum Blattschnitt, seine
Striche treffen die gegenüberliegenden Blatträder rund 200 px versetzt.

**Streufunde verschieben um einen ganzen Kilometer.** Eine Falzkante oder
Rahmenlinie setzt sich fast lückenlos ins Raster; auf dem Blatt 2008 lag genau
so ein Fund einen Rasterschritt vor dem ersten echten Strich und schob das
ganze Blatt um 449 px. Deshalb wird die Kilometerzuordnung nicht entschieden,
sondern **aufgezählt** — jede mögliche Verschiebung, dazu die Fälle mit
verworfenem erstem oder letztem Strich — und die richtige über die
**Randprobe** gefunden: innerhalb des Kartenfelds steht Karte, außerhalb
weißes Papier. Eine falsche Zuordnung legt den Rahmen mitten ins Kartenbild,
und der Tintenkontrast bricht zusammen.

**Blatt 2008 hat je Achse nur ein Randband.** Aus einer einzelnen Strichreihe
ist die Blattdrehung nicht ablesbar (mathematisch, nicht bloß praktisch). Sie
kommt deshalb aus der **Schräge des UTM-Netzes**: zwischen GK-Gitternord und
UTM-Gitternord liegt ein rechenbarer fester Winkel (−2,246° in Blattmitte).
Am Blatt 2001, wo beide Gitter vollständig sind, stimmt der so bestimmte Wert
auf **0,003°** mit dem aus dem Gitter gerechneten überein. Der zuvor
versuchte Weg über die Rahmenlinie streute um 0,11° und war damit zu ungenau —
bei 2008 liegen beide Bänder in derselben Blattecke, dort wirkt ein
Drehungsfehler über die volle Blattdiagonale.

**Ein stimmiger Fit kann trotzdem falsch liegen.** Auf dem Blatt 2008 stammten
**beide** gefundenen Bänder nicht vom Gauß-Krüger-Gitter, sondern vom
**UTM-Netz** — dessen Linien queren dort das Kartenbild, während die
GK-Werte nur als kurze blaue Striche am Rand angerissen sind. Die blaue Marke
liegt im unteren Randfeld 25 px links der schwarzen UTM-Linie; damit steht sie
nicht mehr frei genug für das Sieb in `segmente`, fällt heraus, und die
durchgezogene schwarze Linie bleibt übrig. Elf beziehungsweise zwölf Striche,
ein Kilometer Abstand, Restklaffung 1,2 m: von innen sah nichts falsch aus.
Das Blatt lag **146 m zu weit südlich und 49 m zu weit westlich**.

Deshalb gibt es die **Rahmenprobe**: der gedruckte Blattrahmen ist der
Blattschnitt selbst und damit eine vom Gitter unabhängige Aussage. Gesucht
wird er in neun schmalen Streifen statt in einem Zug über die halbe
Blattbreite — ein Blatt liegt bis zu drei Zehntelgrad schief auf dem Scanner,
und über 3000 px verwischt das eine Linie, bis sie im Profil untergeht.
Weicht das Modell um mehr als 15 px ab, gilt der Rahmen.

Ergebnis über alle Blätter (Abweichung Ost/Nord in px): 1960 +6/+2,
1963 +11/+4, 1984 +9/+10, 1992 +9/+8, 1995 +8/+10, 2001 —/+2,
2008 +29/+70 → **beide Achsen von 2008 kommen aus dem Rahmen**. Der Rahmen von
1969 ist zu blass zum Messen. Die durchgehenden +8 bis +11 px der guten
Blätter sind die Messunsicherheit der Rahmensuche selbst (Doppellinien), nicht
ein Fehler — deshalb liegt die Schwelle bei 15 px.

### Gemessene Passgenauigkeit der Blätter untereinander

Phasenkorrelation der fertigen Kacheln bei Zoom 16 (1 px = 1,58 m), Bezug
1995, Median über bis zu 24 Felder:

| Blatt | Versatz | Bemerkung |
|---|---|---|
| 1960 | nicht messbar | Kartenbild zu verschieden, siehe unten |
| 1963 | nicht messbar | dito |
| 1969 | 0,0 m | 14 Felder, alle auf 0–1 px |
| 1984 | 1,1 m | 20 Felder, alle auf ≤1 px |
| 1992 | 1,1 m | |
| 1995 | — | Bezug |
| 2001 | 3,5 m | |
| 2008 | 6,5 m | vorher **49,5 m** |

**Zu 1960 und 1963.** Beide sind mit ihrem eigenen Gitter sauber gefasst
(2,1/1,2 m rms) und ihr Rahmen bestätigt das. Trotzdem sitzt 1960 gegen die
späteren Ausgaben am Südrand deckungsgleich und driftet zum Nordrand hin um
gut 10 m ab — im Blendbild sind Straße und Höhenlinie dort doppelt zu sehen.
Automatisch **nicht korrigierbar**: von zwanzig Feldern liefern bei 1960 nur
ein bis drei ein Ergebnis, dem zwei unabhängige Bezugsblätter gleichzeitig
zustimmen; die Korrelation scheitert am Stilwechsel (Punktsignaturen,
Schraffuren) und lässt sich auch durch größere Felder oder eine Beschränkung
auf die schwarze Druckplatte nicht retten. Zum Vergleich: bei 1984 sind es
20 von 20 Feldern.

Was bleibt, wäre eine Handvoll **von Hand gesetzter Passpunkte** auf
Merkmalen, die auf beiden Blättern eindeutig sind — Kirchtürme, Brücken,
Straßenkreuzungen. Das ist der eine Fall, in dem sich eine Klick-Oberfläche
wirklich lohnen würde. Bis dahin ist 1960 so referenziert, wie es gedruckt
ist, und die Abweichung liegt zwischen Gitter und Kartenbild des Blattes
selbst, nicht in der Pipeline.

### Probe

`etl/passpunkte.json` hält je Blatt die beiden Achsfits, die Klaffungen, die
Rahmenabweichung, das gerechnete Kartenfeld in Pixeln und den Sollvergleich.
Wer eine Zuordnung von Hand korrigieren will, ändert dort die
Achskoeffizienten — `etl/kacheln.py` liest ausschließlich diese Datei.

Zwei weitere Proben, beide bestanden:

- Derselbe Geo-Punkt (Kastulusmünster) aus allen acht Blättern ausgeschnitten
  zeigt in jedem Ausschnitt dieselbe Umgebung an derselben Stelle.
- Eine Kachel von 1969 über dieselbe Kachel der heutigen Basiskarte gelegt:
  Straßenzüge, Stadtgraben und Kirchenstandorte decken sich.

Und eine Faustregel, die aus dem 2008er Fehler folgt: **die Kachelränder
anschauen.** Bleibt am Blattrand ein Streifen der Randleiste stehen, sitzt das
Blatt falsch — schneller und schärfer als jede Klaffungsstatistik.

---

## 4. Kacheln (`etl/kacheln.py`)

Web Mercator → WGS84 → Gauß-Krüger → Blattpixel. Exakt gerechnet wird nur auf
einem 16-px-Stützgitter, dazwischen linear interpoliert — über wenige hundert
Pixel ist die Abbildung praktisch affin, das spart den Großteil der
Projektionsrechnung ohne messbaren Fehler.

- **Beschnitt auf den Blattschnitt selbst**, nicht auf den Scanrand, um 9 px
  eingerückt. Damit verschwinden Rahmen, Randleiste und Legende — und die
  unterschiedlichen Layouts der Faltkarten spielen keine Rolle mehr.
- Zoom 10–16, 256-px-Kacheln, **WebP q72**, eine PMTiles-Datei je Jahrgang in
  `public/data/<jahr>.pmtiles`. Rund 12 MB je Blatt.
- Mipmaps gegen Flimmern in tiefen Zoomstufen; die Stufenwahl rechnet in
  **Web-Mercator-Metern**, nicht in Bodenmetern (Faktor 1/cos φ = 1,51).
- Randkacheln bekommen Alpha, volle Kacheln werden ohne Alphakanal
  geschrieben.

Laufzeit rund 2,5 min je Blatt, das meiste davon WebP mit `method=6`.

---

## 5. App

Stack wie die Geschwister: **Vite 6 + React 19 + TypeScript + Tailwind v4**,
**MapLibre GL JS 5 + PMTiles 4**, Fonts via `@fontsource`. Kein Router.

**Basiskarte der Gegenwart:** TopPlusOpen des BKG
(`sgx.geodatenzentrum.de/wmts_topplus_open/…`, CORS offen, ohne Schlüssel).
Bewusst eine topographische Karte und kein Luftbild: derselbe Register wie die
alten Blätter, dadurch der ehrlichste Vergleich. Sie liegt **immer** unter den
Blättern, deshalb bleibt der Rand des Blattschnitts orientierbar. „Heute" auf
der Zeitschiene heißt schlicht: kein historisches Blatt darüber.

**Das Instrument ist die Zeitschiene.** Ein Lineal mit echten Jahresabständen
von 1960 bis heute, eine Marke je vorhandener Ausgabe. Die ungleichen Abstände
sind selbst eine Aussage — zwischen 1969 und 1984 liegen fünfzehn Jahre ohne
neues Blatt. Der Schieber rastet auf die Ausgaben ein; **gehalten wird nie ein
Mischbild**, weil zwei halbtransparente Karten übereinander unlesbar sind.
Bewegt man ihn, blendet MapLibre über `raster-opacity-transition` in 450 ms
über.

Die Marken hängen **über** dem Lineal und stoßen an es an, statt es zu
überlagern — so kommen sie dem Schieber nicht in die Quere und sind trotzdem
anklickbar. Farbe Gold für die vorhandenen Ausgaben, Rot und doppelte Breite
für die gewählte. Aus dem Tastaturpfad sind sie ausgenommen (`tabIndex={-1}`):
der Regler selbst ist bereits bedienbar, neun zusätzliche Tab-Stationen wären
nur im Weg.

Nicht in der ersten Fassung: der Vorhang-Vergleich mit senkrechter Trennlinie.
Er braucht eine zweite, synchronisierte Karteninstanz und lohnt erst, wenn die
Zeitschiene im Gebrauch steht.

Design nach dem Kartenblatt-Konzept der Baumkarte: deckendes Cream statt Glas,
eckige Ecken, Playfair-Versalien, Tabellenziffern, 2px-Goldregel als
Blattkante, Quellenvermerk fest im Randblock (MapLibre-Attribution aus).
Farbakzente nur Gold und Rot. **Kein einseitiger Kantenakzent** (siehe
`moosburg-eu/BRIEFING.md`).

---

## 6. Deployment

Zwei Ziele aus einem Branch, wie bei der Baumkarte:

- **GitHub Pages** — `.github/workflows/deploy.yml`, Basis `/moosburghistorisch/`
- **moosburg.eu** — `.github/workflows/hostinger.yml`, Basis `/data/historisch/`,
  `server-dir: data/historisch/`, Secrets `FTP_HOST`/`FTP_USER`/`FTP_PASSWORD`
  (ohne Präfix), `timeout: 300000`

`public/.htaccess` schaltet gzip für `.pmtiles` ab — sonst verschieben sich die
Byte-Offsets der Range-Requests und die Karte bleibt kommentarlos leer. Auf
moosburg.eu geprüft: Range-Request auf `1960.pmtiles` liefert **206** mit
korrektem `Content-Range` und ohne `Content-Encoding`.

**Beide Ziele laufen** (19.08.2026), im Browser gegen die echten Adressen
getestet, keine Konsolenfehler. Eine Warnung aus der Praxis: Der Push dieses
Repos und der von `datahub` kurz danach haben sich am gemeinsamen FTP-Konto
gestoßen — der Data-Hub-Lauf endete in `Timeout (control socket)`, obwohl
sein Timeout bei 120 s liegt. Nach dem 93-MB-Upload braucht Hostinger länger.
Ein erneuter Lauf genügte. Also: **nacheinander deployen, nicht parallel.**

Die `exclude`-Liste des `moosburg-eu`-Workflows braucht **keinen** Eintrag:
sie führt bereits `data/**`, und darunter liegt der neue Ordner. Die Card im
Data Hub ist ergänzt (`datahub/src/pages/Home.tsx`, Abschnitt „Karten", neben
der Baumkarte); die beiden Karten teilen sich dort jetzt eine kleine
`KartenCard`-Komponente, statt vierzig Zeilen Markup doppelt zu tragen.

---

## 7. Offen

1. **Ältere Blätter.** 1960 ist für eine Stadt dieser Geschichte spät. Bayern
   hält Urpositionsblätter (1817–1841) und die Uraufnahme (1808–1864) vor.
   Wenn es dafür einen offenen Dienst gibt, wäre das der größte Zugewinn im
   Projekt — noch nicht geprüft.
2. **Luftbild als zweite Gegenwart.** Die DOP20 der bayerischen
   Vermessungsverwaltung sind offene Daten; die WMTS-Adresse unter
   `geoservices.bayern.de/od/wmts/dop/…` hat auf gut geratene Pfade mit 404
   geantwortet, die Capabilities müssen noch gesucht werden.
3. **Vorhang-Vergleich** (zwei synchronisierte Karten, ziehbare Trennlinie).
4. **Blattrand als eigene Ansicht.** Die Zeichenerklärungen der Jahrgänge sind
   historisch interessant und fallen beim Beschnitt weg.
5. **Nutzungsrechte.** Die Scans tragen den Stempel „Historische Sammlung,
   Topogr. Archiv, Bayer. Landesvermessungsamt". Quellenangabe steht im
   Randblock; ob die Archivscans unter die offene Lizenz der übrigen
   LDBV-Daten fallen, ist nicht abschließend geklärt.

## Changelog

- **20.08.2026** — Rahmenprobe auf beide Achsen ausgeweitet und in Streifen
  gesucht. Damit 2008 von 49,5 m auf 6,5 m Versatz gebracht: dort hingen
  *beide* Achsen am UTM-Netz. Passgenauigkeit aller Blätter untereinander
  gemessen (Abschnitt 3). Marken der Zeitschiene sichtbar und anklickbar.
- **19.08.2026 (2)** — Beide Deploys scharf geschaltet und an den echten
  Adressen geprüft, Card im Data Hub live. Der Hostinger-Lauf von `datahub`
  scheiterte beim ersten Versuch am gemeinsamen FTP-Konto (Abschnitt 6).
- **19.08.2026** — Erste Fassung. Georeferenzierung über das Kilometergitter
  aufgebaut und an allen acht Blättern verifiziert (Klaffung ≤ 3 m rms),
  Kachelpipeline nach PMTiles, App mit Zeitschiene, beide Deploy-Workflows.
