import { useState } from "react";
import { AUSGABEN, ERSTES, HEUTE, lage, naechsteStufe, STUFEN } from "@/lib/jahre";

/**
 * Randblock des Kartenblatts. Sein Instrument ist die Zeitschiene: ein Lineal
 * mit echten Jahresabstaenden, auf dem jede vorhandene Ausgabe eine Marke hat.
 * Die ungleichen Abstaende sind selbst eine Aussage -- zwischen 1969 und 1984
 * liegen fuenfzehn Jahre ohne neues Blatt.
 */
export function Randblock({
  jahr,
  onJahr,
  laedt,
}: {
  jahr: number;
  onJahr: (j: number) => void;
  laedt: boolean;
}) {
  const [offen, setOffen] = useState(false);
  const ausgabe = AUSGABEN.find((a) => a.jahr === jahr);

  return (
    <section className="plate-scroll absolute inset-x-0 bottom-0 z-10 max-h-[46dvh] overflow-y-auto border-t border-ink-frame bg-cream px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-[0_-2px_12px_rgb(0_0_0/0.07)] sm:inset-x-auto sm:bottom-auto sm:left-4 sm:top-4 sm:max-h-[calc(100dvh-2rem)] sm:w-[21rem] sm:rounded-sm sm:border sm:px-4 sm:pb-4 sm:pt-4 sm:shadow-soft">
      <p className="eyebrow text-red-700">
        {laedt ? "Blatt wird geladen …" : "Moosburg an der Isar"}
      </p>
      <h1 className="headline mt-1 text-[1.35rem] sm:text-[1.5rem]">Karten der Zeit</h1>
      <p className="mt-1.5 mb-3 text-[0.75rem] text-ink-soft">
        Topographische Karte 1:25 000, Blatt 7537 — acht Ausgaben, deckungsgleich
        übereinandergelegt.
      </p>

      {/* Goldregel als Blattkante, wie in der Baumkarte */}
      <div className="-mx-4 h-[2px] bg-gold-500" />

      <div className="mt-3 flex items-baseline justify-between">
        <span className="label">Ausgabe</span>
        <span className="font-display text-[1.6rem] leading-none tabular-nums text-ink">
          {jahr === HEUTE ? "heute" : jahr}
        </span>
      </div>

      <Zeitschiene jahr={jahr} onJahr={onJahr} />

      <p className="mt-3 min-h-[2.4rem] text-[0.75rem] leading-snug text-ink-soft">
        {ausgabe
          ? ausgabe.notiz
          : "Amtliche Basiskarte des Bundes, Stand der laufenden Fortführung."}
      </p>

      <button
        type="button"
        onClick={() => setOffen(!offen)}
        className="mt-2 text-[0.72rem] font-semibold text-red-700 underline underline-offset-2"
      >
        {offen ? "Erläuterung schließen" : "Woher die Karten kommen"}
      </button>
      {offen && (
        <div className="mt-2 space-y-2 text-[0.72rem] leading-snug text-ink-soft">
          <p>
            Die acht Blätter sind Archivscans der Topographischen Karte 1:25 000,
            Blatt 7537 Moosburg a.d.Isar. Jedes deckt dieselbe Fläche ab: 11°50′
            bis 12°00′ östlicher Länge, 48°24′ bis 48°30′ nördlicher Breite.
          </p>
          <p>
            Passgenau werden sie über ihr eigenes Kilometergitter. Die alten
            Blätter tragen die Gradangaben noch auf dem Bessel-Datum — wer sie
            für heutige Koordinaten nimmt, legt die Karte rund 150 Meter
            daneben.
          </p>
          <p>
            Für die Gegenwart liegt keine eigene Ebene bereit; dort steht die
            amtliche Basiskarte, damit der Vergleich im selben Register bleibt.
          </p>
        </div>
      )}

      <p className="mt-3 border-t border-ink-line pt-2 text-[0.66rem] leading-snug text-ink-muted">
        Kartengrundlage: Bayerische Vermessungsverwaltung. Gegenwart: TopPlusOpen,
        © Bundesamt für Kartographie und Geodäsie.
      </p>
    </section>
  );
}

function Zeitschiene({ jahr, onJahr }: { jahr: number; onJahr: (j: number) => void }) {
  return (
    <div className="relative mt-2 pb-4">
      {/* Marken der vorhandenen Ausgaben, auf echten Jahresabstaenden */}
      <div className="pointer-events-none absolute inset-x-0 top-[7px] h-[10px]">
        {STUFEN.map((s) => (
          <span
            key={s}
            className={`absolute top-0 w-px ${
              s === jahr ? "h-[10px] bg-red-600" : "h-[5px] bg-ink-line"
            }`}
            style={{ left: `${lage(s) * 100}%` }}
          />
        ))}
      </div>
      <input
        type="range"
        className="rule-slider relative"
        min={ERSTES}
        max={HEUTE}
        step={1}
        value={jahr}
        aria-label="Ausgabejahr"
        aria-valuetext={jahr === HEUTE ? "heute" : String(jahr)}
        onChange={(e) => onJahr(naechsteStufe(Number(e.target.value)))}
        // Die Tasten muessen von Ausgabe zu Ausgabe springen. Ueberliesse man
        // sie dem Schrittwert, bewegten sie den Wert um ein Jahr -- und die
        // Rastung schoebe ihn sofort wieder zurueck.
        onKeyDown={(e) => {
          const schritt =
            e.key === "ArrowLeft" || e.key === "ArrowDown"
              ? -1
              : e.key === "ArrowRight" || e.key === "ArrowUp"
                ? 1
                : 0;
          if (!schritt && e.key !== "Home" && e.key !== "End") return;
          e.preventDefault();
          const i = STUFEN.indexOf(jahr);
          const ziel =
            e.key === "Home"
              ? 0
              : e.key === "End"
                ? STUFEN.length - 1
                : Math.min(Math.max(i + schritt, 0), STUFEN.length - 1);
          onJahr(STUFEN[ziel]);
        }}
      />
      <div className="mt-1 flex justify-between text-[0.62rem] tabular-nums text-ink-muted">
        <span>{ERSTES}</span>
        <span>heute</span>
      </div>
    </div>
  );
}
