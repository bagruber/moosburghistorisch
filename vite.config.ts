import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  // GitHub Pages liegt unter /moosburghistorisch/ (Repo-Name). Auf moosburg.eu
  // haengen die Karten am Data Hub, dort setzt `npm run build:hostinger` den
  // Pfad auf /data/historisch/.
  base: "/moosburghistorisch/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
});
