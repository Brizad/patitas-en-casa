// Pruebas de punta a punta (#233). La instancia (API + PostgreSQL + panel compilado + PWA) se
// arranca aparte; ver docs/aprende/e2e.md. Aquí solo se dice dónde está y qué navegador usar.
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.mjs",
  fullyParallel: false, // un solo flujo con datos compartidos: en orden
  workers: 1,
  retries: 0,
  timeout: 60_000,
  reporter: [["list"], ["html", { open: "never", outputFolder: "informe" }]],
  outputDir: "resultados",
  use: {
    baseURL: process.env.E2E_URL ?? "http://127.0.0.1:8010",
    // En el CI, Google Chrome del runner; en Windows, Edge (E2E_CANAL=msedge).
    channel: process.env.E2E_CANAL ?? "chrome",
    serviceWorkers: "block", // la PWA no debe responder desde la caché durante la prueba
    locale: "es-CO",
    timezoneId: "America/Bogota",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
