// Panel del personal (II-03, #64). Se compila a app/panel_web y la API lo sirve en /panel/.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API = "http://127.0.0.1:8000";

export default defineConfig({
  base: "/panel/",
  plugins: [react()],
  build: { outDir: "../app/panel_web", emptyOutDir: true },
  // En desarrollo (npm run dev) las llamadas a la API pasan por el mismo origen.
  server: { proxy: { "/auth": API, "/cola": API, "/reportes": API } },
  test: { environment: "node" },
});
