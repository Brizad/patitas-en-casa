// Capturas del estado actual (25-nov) para decidir el diseño con mockups: sin cambiar nada.
// Portada, PWA (reportar y consultar), cola y detalle del veterinario, y la pantalla de inicio
// del coordinador, del rescatista y del adoptante; a 360 y 1366 px, en claro y oscuro.
//
//   PATITAS_DEMO_CONTRASENA=... node estado_actual.mjs [http://127.0.0.1:8000]
//
// Guarda JPEG de página completa en docs/revision-visual/estado-actual/<ancho>-<tema>-<pantalla>.jpg.
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const BASE = process.argv[2] ?? "http://127.0.0.1:8000";
const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const CARPETA = fileURLToPath(new URL("../../docs/revision-visual/estado-actual/", import.meta.url));
if (!CLAVE) {
  console.error("Falta PATITAS_DEMO_CONTRASENA (la misma del servidor).");
  process.exit(2);
}
mkdirSync(CARPETA, { recursive: true });

async function capturar(pagina, prefijo, nombre) {
  await pagina.waitForLoadState("networkidle");
  await pagina.waitForTimeout(700); // React pide los datos después de pintar
  await pagina.screenshot({ path: `${CARPETA}${prefijo}-${nombre}.jpg`, fullPage: true,
    type: "jpeg", quality: 60, animations: "disabled", caret: "hide" });
}

async function entrar(pagina, usuario) {
  await pagina.goto(`${BASE}/panel/`);
  await pagina.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await pagina.getByLabel("Contraseña").fill(CLAVE);
  await pagina.getByRole("button", { name: "Entrar" }).click();
  await pagina.getByRole("button", { name: "Salir" }).waitFor();
}

const navegador = await chromium.launch({ channel: process.env.A11Y_CANAL ?? "chrome" });
let total = 0;
for (const tema of ["claro", "oscuro"]) {
  for (const ancho of [360, 1366]) {
    const contexto = await navegador.newContext({
      colorScheme: tema === "claro" ? "light" : "dark", locale: "es-CO",
      timezoneId: "America/Bogota", serviceWorkers: "block", deviceScaleFactor: 1,
      viewport: { width: ancho, height: ancho === 360 ? 780 : 800 },
    });
    const pagina = await contexto.newPage();
    const prefijo = `${ancho}-${tema}`;
    for (const [nombre, ruta] of [["portada", "/"], ["pwa-reportar", "/app/#reportar"],
      ["pwa-consultar", "/app/#estado"]]) {
      await pagina.goto(BASE + ruta);
      await capturar(pagina, prefijo, nombre);
      total++;
    }
    await entrar(pagina, "veterinaria");
    await capturar(pagina, prefijo, "veterinario-cola");
    await pagina.locator(".cola .item").first().click();
    await capturar(pagina, prefijo, "veterinario-detalle");
    total += 2;
    await pagina.getByRole("button", { name: "Salir" }).click();
    for (const usuario of ["coordinador", "rescatista", "adoptante"]) {
      await entrar(pagina, usuario);
      await capturar(pagina, prefijo, `${usuario}-inicio`);
      total++;
      await pagina.getByRole("button", { name: "Salir" }).click();
    }
    await contexto.close();
  }
}
await navegador.close();
console.log(`${total} capturas en docs/revision-visual/estado-actual/`);
