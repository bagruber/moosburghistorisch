import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";
import { Randblock } from "@/components/Randblock";
import { AUSGABEN } from "@/lib/jahre";
import { BLATT, blaetterHinzu, grundstil, zeige } from "@/lib/karte";

/** Padding fuer fitBounds: mobil liegt der Randblock unten, ab sm links. */
function randabstand() {
  const schmal = window.innerWidth < 640;
  return schmal
    ? { top: 16, right: 16, bottom: Math.round(window.innerHeight * 0.46) + 8, left: 16 }
    : { top: 16, right: 16, bottom: 16, left: 360 };
}

export default function App() {
  const behaelter = useRef<HTMLDivElement>(null);
  const karte = useRef<maplibregl.Map | null>(null);
  const [jahr, setJahr] = useState(AUSGABEN[0].jahr);
  const vorher = useRef<string | null>(null);
  const [bereit, setBereit] = useState(false);

  useEffect(() => {
    if (!behaelter.current) return;
    const protokoll = new Protocol();
    maplibregl.addProtocol("pmtiles", protokoll.tile);

    const m = new maplibregl.Map({
      container: behaelter.current,
      style: grundstil(),
      bounds: [BLATT[0], BLATT[1], BLATT[2], BLATT[3]],
      // Der Randblock sitzt mobil unten, am Desktop oben links -- das Blatt
      // bekommt deshalb asymmetrisch Luft, damit er keine Karte verdeckt.
      fitBoundsOptions: { padding: randabstand() },
      // Das Blatt ist der ganze Gegenstand -- weiter hinaus gibt es nichts
      // zu sehen, also endet die Karte auch dort.
      maxBounds: [BLATT[0] - 0.05, BLATT[1] - 0.04, BLATT[2] + 0.05, BLATT[3] + 0.04],
      minZoom: 11,
      maxZoom: 18,
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
    });
    m.touchZoomRotate.disableRotation();
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: "metric" }), "bottom-right");

    m.on("load", () => {
      blaetterHinzu(m, import.meta.env.BASE_URL);
      vorher.current = AUSGABEN[0].id;
      zeige(m, null, AUSGABEN[0].id, true);
      setBereit(true);
    });

    karte.current = m;
    return () => {
      m.remove();
      maplibregl.removeProtocol("pmtiles");
      karte.current = null;
    };
  }, []);

  useEffect(() => {
    if (!karte.current || !bereit) return;
    const ziel = AUSGABEN.find((a) => a.jahr === jahr)?.id ?? null;
    zeige(karte.current, vorher.current, ziel, false);
    vorher.current = ziel;
  }, [jahr, bereit]);

  return (
    <main className="relative h-dvh w-screen overflow-hidden">
      <div ref={behaelter} className="h-full w-full" />
      <Randblock jahr={jahr} onJahr={setJahr} laedt={!bereit} />
    </main>
  );
}
