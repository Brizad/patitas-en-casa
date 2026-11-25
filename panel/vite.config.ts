// Panel del personal (II-03, #64). Se compila a app/panel_web y la API lo sirve en /panel/.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API = "http://127.0.0.1:8000";

export default defineConfig({
  base: "/panel/",
  plugins: [react()],
  // #430: nada como data: (la CSP solo admite imágenes de 'self'): el pin de Leaflet pesa < 4 KB.
  build: { outDir: "../app/panel_web", emptyOutDir: true, assetsInlineLimit: 0 },
  // En desarrollo (npm run dev) las llamadas a la API pasan por el mismo origen.
  server: { proxy: Object.fromEntries(
    ["/auth", "/cola", "/reportes", "/rescates", "/rescatistas", "/refugio", "/admin",
     "/adoptantes", "/adopciones", "/indicadores", "/bitacora", "/diseno", "/app"]
      .map((ruta) => [ruta, API])) },
  test: { environment: "node" },
});
