// Revisión visual y de experiencia (24-nov): captura TODAS las pantallas de cada rol a 360 y
// 1366 px, en claro y oscuro, para mirarlas lado a lado antes y después de los arreglos.
//
//   PATITAS_DEMO_CONTRASENA=... node revision_visual.mjs <antes|despues> [http://127.0.0.1:8000]
//
// Guarda JPEG de página completa en docs/revision-visual/<carpeta>/ con nombres
// <ancho>-<tema>-<pantalla>.jpg. Navegador: Chrome (A11Y_CANAL=msedge para Edge).
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const CARPETA_DESTINO = process.argv[2] ?? "antes";
const BASE = process.argv[3] ?? "http://127.0.0.1:8000";
const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const CARPETA = fileURLToPath(new URL(`../../docs/revision-visual/${CARPETA_DESTINO}/`,
                                      import.meta.url));
const ROLES = ["veterinaria", "coordinador", "rescatista", "adoptante", "admin", "alcaldia"];
const PUBLICAS = [
  ["inicio", "/"],
  ["pwa-reportar", "/app/#reportar"],
  ["pwa-consultar", "/app/#estado"],
  ["panel-entrar", "/panel/"],
  ["panel-registro", "/panel/#registro"],
];
if (!CLAVE) {
  console.error("Falta PATITAS_DEMO_CONTRASENA (la misma del servidor).");
  process.exit(2);
}
mkdirSync(CARPETA, { recursive: true });

const simple = (texto) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
  .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

async function capturar(pagina, ancho, tema, nombre) {
  await pagina.waitForLoadState("networkidle");
  await pagina.waitForTimeout(700); // React pide los datos después de pintar la pestaña
  await pagina.screenshot({
    path: `${CARPETA}${ancho}-${tema}-${nombre}.jpg`, fullPage: true, type: "jpeg", quality: 60,
    animations: "disabled", caret: "hide",
  });
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
    for (const [nombre, ruta] of PUBLICAS) {
      await pagina.goto(BASE + ruta);
      await capturar(pagina, ancho, tema, nombre);
      total++;
    }
    for (const usuario of ROLES) {
      await entrar(pagina, usuario);
      const pestanas = pagina.locator('nav[aria-label="Secciones"] button');
      const cuantas = await pestanas.count();
      if (cuantas === 0) await capturar(pagina, ancho, tema, `panel-${usuario}`);
      for (let i = 0; i < cuantas; i++) {
        const titulo = simple(await pestanas.nth(i).innerText());
        await pestanas.nth(i).click();
        await capturar(pagina, ancho, tema, `panel-${usuario}-${titulo}`);
        total++;
      }
      await pagina.getByRole("button", { name: "Salir" }).click();
    }
    await contexto.close();
  }
}
await navegador.close();
console.log(`${total} capturas en docs/revision-visual/${CARPETA_DESTINO}/`);
