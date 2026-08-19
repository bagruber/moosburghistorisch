/** Die vorhandenen Blattausgaben und ihre Lage auf der Zeitachse. */
export type Ausgabe = {
  jahr: number;
  /** Kennung der Kartenebene in MapLibre. */
  id: string;
  /** Kurzcharakteristik fuer die Erlaeuterung im Randblock. */
  notiz: string;
};

export const AUSGABEN: Ausgabe[] = [
  { jahr: 1960, id: "blatt-1960", notiz: "Nachkriegsausgabe, Höhenlinien in Braun, Ort noch klar begrenzt" },
  { jahr: 1963, id: "blatt-1963", notiz: "Fortführung der 60er-Ausgabe" },
  { jahr: 1969, id: "blatt-1969", notiz: "Erste Ausgabe im neuen Kartenbild, Siedlungsflächen grau" },
  { jahr: 1984, id: "blatt-1984", notiz: "Nach fünfzehn Jahren ohne Neuausgabe" },
  { jahr: 1992, id: "blatt-1992", notiz: "Fortführung" },
  { jahr: 1995, id: "blatt-1995", notiz: "Letzte Ausgabe im schwarz-grauen Kartenbild" },
  { jahr: 2001, id: "blatt-2001", notiz: "Faltkarte, farbiges Kartenbild, UTM-Gitter zusätzlich" },
  { jahr: 2008, id: "blatt-2008", notiz: "Letzte gedruckte Ausgabe dieses Blattes" },
];

/** Die Gegenwart als eigene Stufe: hier liegt kein Blatt, sondern die Basiskarte. */
export const HEUTE = 2026;
export const ERSTES = AUSGABEN[0].jahr;

/** Alle Stufen der Zeitschiene, die Gegenwart eingeschlossen. */
export const STUFEN = [...AUSGABEN.map((a) => a.jahr), HEUTE];

/** Nächstgelegene Stufe zu einem beliebigen Jahr auf der Schiene. */
export function naechsteStufe(jahr: number): number {
  return STUFEN.reduce((a, b) => (Math.abs(b - jahr) < Math.abs(a - jahr) ? b : a));
}

/** Lage eines Jahres auf der Schiene, 0 bis 1. */
export function lage(jahr: number): number {
  return (jahr - ERSTES) / (HEUTE - ERSTES);
}
