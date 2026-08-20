import maplibregl from "maplibre-gl";
import { AUSGABEN } from "./jahre";

/** Blattschnitt von 7537 in WGS84: West, Sued, Ost, Nord. Gerechnet aus den
 *  gedruckten Bessel-Gradangaben 11 Grad 50' bis 12 Grad, 48 Grad 24' bis
 *  48 Grad 30' -- der Datumsuebergang verschiebt sie um rund 150 m. */
export const BLATT: [number, number, number, number] = [
  11.8319, 48.39905, 11.99855, 48.49904,
];

/** Anteil des Blattes, der im aeussersten Schwenk noch im Bild stehen soll. */
const REST = 0.2;

/** Wie weit die Karte ueber den Blattrand hinaus darf, haengt davon ab,
 *  wieviel Karte ueberhaupt ins Fenster passt: das Fenster darf so weit
 *  wandern, bis vom Blatt noch REST uebrig ist. Ein fester Ueberstand kann
 *  das nicht leisten -- am Telefon ist das Sichtfeld schmaler als das Blatt,
 *  am Schreibtisch anderthalbmal so breit. Gerechnet wird deshalb aus dem
 *  eingepassten Blick, nicht aus der Blattgroesse. */
export function schwenkgrenzen(karte: maplibregl.Map): maplibregl.LngLatBoundsLike {
  const sicht = karte.getBounds();
  const ueber = (weite: number, mass: number) =>
    Math.max(weite - mass * REST, 0);
  const x = ueber(sicht.getEast() - sicht.getWest(), BLATT[2] - BLATT[0]);
  const y = ueber(sicht.getNorth() - sicht.getSouth(), BLATT[3] - BLATT[1]);
  return [BLATT[0] - x, BLATT[1] - y, BLATT[2] + x, BLATT[3] + y];
}

/** Basiskarte der Gegenwart. Amtlich, ohne Schluessel, CORS offen -- und im
 *  Register einer topographischen Karte, also direkt mit den Blaettern
 *  vergleichbar. */
const TOPPLUS =
  "https://sgx.geodatenzentrum.de/wmts_topplus_open/tile/1.0.0/web/default/WEBMERCATOR/{z}/{y}/{x}.png";

export const UEBERBLENDUNG = 450;

export function grundstil(): maplibregl.StyleSpecification {
  return {
    version: 8,
    sources: {
      heute: {
        type: "raster",
        tiles: [TOPPLUS],
        tileSize: 256,
        minzoom: 0,
        maxzoom: 18,
      },
    },
    layers: [
      { id: "grund", type: "background", paint: { "background-color": "#faf7f2" } },
      { id: "heute", type: "raster", source: "heute", paint: { "raster-opacity": 1 } },
    ],
  };
}

/** Die acht Blaetter als Rasterebenen, aelteste unten. Alle beginnen
 *  unsichtbar; sichtbar wird immer nur die gewaehlte und, waehrend der
 *  Ueberblendung, ihre Vorgaengerin. */
export function blaetterHinzu(karte: maplibregl.Map, basis: string) {
  for (const ausgabe of AUSGABEN) {
    karte.addSource(ausgabe.id, {
      type: "raster",
      url: `pmtiles://${basis}data/${ausgabe.jahr}.pmtiles`,
      tileSize: 256,
    });
    karte.addLayer({
      id: ausgabe.id,
      type: "raster",
      source: ausgabe.id,
      layout: { visibility: "none" },
      paint: {
        "raster-opacity": 0,
        "raster-opacity-transition": { duration: UEBERBLENDUNG, delay: 0 },
        // Ohne diese Bremse mischt MapLibre benachbarte Zoomstufen und das
        // Kartenbild wird beim Zoomen doppelt gezeichnet.
        "raster-fade-duration": 0,
      },
    });
  }
}

/**
 * Blendet von einer Ausgabe auf die naechste um; `null` steht fuer die
 * Gegenwart, also fuer die Basiskarte unter allen Blaettern.
 *
 * Die Richtung entscheidet, welche der beiden Ebenen bewegt wird. Geht es
 * vorwaerts, liegt das Ziel oben und wird eingeblendet, waehrend die
 * Vorgaengerin deckend stehenbleibt. Geht es zurueck, liegt das Ziel unten:
 * dann wird es sofort deckend gesetzt und die Vorgaengerin darueber
 * ausgeblendet. Beides zugleich zu bewegen sieht schlechter aus, als es
 * klingt -- an der Halbzeit summieren sich zwei halbdurchsichtige Ebenen
 * nicht zu einer deckenden, und die Basiskarte blitzt durch.
 */
export function zeige(
  karte: maplibregl.Map,
  von: string | null,
  nach: string | null,
  sofort: boolean,
) {
  const ids = AUSGABEN.map((a) => a.id);
  const rang = (id: string | null) => (id ? ids.indexOf(id) : -1);

  for (const id of ids) {
    if (id !== von && id !== nach) karte.setLayoutProperty(id, "visibility", "none");
  }
  if (nach) karte.setLayoutProperty(nach, "visibility", "visible");

  if (sofort || von === null || von === nach) {
    if (nach) karte.setPaintProperty(nach, "raster-opacity", 1);
    if (von && von !== nach) karte.setLayoutProperty(von, "visibility", "none");
    return;
  }

  if (rang(nach) > rang(von)) {
    karte.setPaintProperty(nach!, "raster-opacity", 0);
    // Ein Frame Abstand, damit MapLibre die 0 als Ausgangswert der
    // Ueberblendung uebernimmt statt sie zu ueberspringen.
    requestAnimationFrame(() => karte.setPaintProperty(nach!, "raster-opacity", 1));
  } else {
    if (nach) karte.setPaintProperty(nach, "raster-opacity", 1);
    karte.setPaintProperty(von, "raster-opacity", 0);
  }

  window.setTimeout(() => {
    karte.setLayoutProperty(von, "visibility", "none");
  }, UEBERBLENDUNG + 60);
}
