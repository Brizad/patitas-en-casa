// Revisión de accesibilidad (RNF-11, WCAG 2.2 AA) de la página de inicio, la PWA y el panel.
//
// - axe-core en cada pantalla (públicas y las de cada rol después de iniciar sesión), en
//   modo claro y oscuro, porque el contraste cambia con el tema; en celular (320 px) también
//   el reflujo, y ahí se revisan los roles que trabajan desde el teléfono.
// - Lighthouse (categoría accesibilidad) en las pantallas públicas; puntaje mínimo 100.
//
// Necesita el servidor de demostración corriendo (servidor_demo.py) y la misma contraseña:
//   PATITAS_DEMO_CONTRASENA=... node revisar.mjs [http://127.0.0.1:8765]
// Navegador: Chrome instalado (A11Y_CANAL=msedge para Edge, CHROME_PATH para Lighthouse).
// Sale con código 1 si hay alguna falla. Deja el detalle en informe.json.
import { writeFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import * as chromeLauncher from "chrome-launcher";
import lighthouse from "lighthouse";
import { chromium } from "playwright-core";

const BASE = process.argv[2] ?? "http://127.0.0.1:8765";
const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const CANAL = process.env.A11Y_CANAL ?? "chrome";
const ETIQUETAS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"];
const PUNTAJE_MINIMO = 100;
const ROLES = ["veterinaria", "coordinador", "rescatista", "adoptante", "admin", "alcaldia"];
const PUBLICAS = [
  ["Inicio", "/"],
  ["PWA · Reportar", "/app/#reportar"],
  ["PWA · Consultar", "/app/#estado"],
  ["Panel · Iniciar sesión", "/panel/"],
  ["Panel · Registro de adoptante", "/panel/#registro"],
];

if (!CLAVE) {
  console.error("Falta PATITAS_DEMO_CONTRASENA (la misma del servidor de demostración).");
  process.exit(2);
}

const resultados = [];

async function revisar(pagina, nombre) {
  await pagina.waitForLoadState("networkidle");
  await pagina.waitForTimeout(700);  // React pide los datos después de pintar la pestaña
  const { violations, incomplete, passes } =
    await new AxeBuilder({ page: pagina }).withTags(ETIQUETAS).analyze();
  const tema = await pagina.evaluate(() =>
    matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro");
  resultados.push({
    pantalla: nombre, tema, herramienta: "axe-core", reglas_cumplidas: passes.length,
    fallas: [...violations.map((v) => ({
      regla: v.id, impacto: v.impact, ayuda: v.help,
      nodos: v.nodes.map((n) => n.target.join(" ")).slice(0, 5),
    })), ...(await reflujo(pagina))],
    // axe no puede decidir estas solas (por ejemplo, contraste sobre un degradado): a mano.
    revisar_a_mano: incomplete.map((v) => v.id),
  });
}

// WCAG 1.4.10 (axe no lo mide): a 320 px de ancho no debe aparecer desplazamiento horizontal.
async function reflujo(pagina) {
  const { ancho, visible } = await pagina.evaluate(() => (
    { ancho: document.documentElement.scrollWidth, visible: innerWidth }));
  return visible <= 320 && ancho > visible
    ? [{ regla: "reflujo-320px", impacto: "serious", ayuda: `la página mide ${ancho} px` }]
    : [];
}

async function entrar(pagina, usuario) {
  await pagina.goto(`${BASE}/panel/`);
  await pagina.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await pagina.getByLabel("Contraseña").fill(CLAVE);
  await pagina.getByRole("button", { name: "Entrar" }).click();
  await pagina.getByRole("button", { name: "Salir" }).waitFor();
}

async function recorrerRol(pagina, usuario) {
  await entrar(pagina, usuario);
  const pestanas = pagina.locator('nav[aria-label="Secciones"] button');
  const total = await pestanas.count();
  if (total === 0) return revisar(pagina, `Panel · ${usuario}`);
  for (let i = 0; i < total; i++) {
    const nombre = await pestanas.nth(i).innerText();
    await pestanas.nth(i).click();
    await revisar(pagina, `Panel · ${usuario} · ${nombre}`);
  }
}

async function reportar(pagina) {
  // El reporte crea un código: así se revisan también las pantallas de código y de estado.
  await pagina.goto(`${BASE}/app/#reportar`);
  await pagina.locator("#descripcion").fill("Perro herido en la calle, cojea y no se levanta bien");
  await pagina.locator("#direccion").fill("Barrio La Playa, calle 10");
  await pagina.locator('#reporte button[type="submit"]').click();
  await pagina.waitForURL(/#codigo/);
  await revisar(pagina, "PWA · Código de seguimiento");
  await pagina.locator("#ver-estado").click();
  await pagina.locator("#resultado").waitFor();
  await revisar(pagina, "PWA · Estado del reporte");
}

const navegador = await chromium.launch({ channel: CANAL });
for (const esquema of ["light", "dark"]) {
  for (const movil of [false, true]) {
    if (movil && esquema === "dark") continue; // celular solo en claro: el diseño es el mismo
    const contexto = await navegador.newContext({
      colorScheme: esquema, locale: "es-CO", serviceWorkers: "block",
      viewport: movil ? { width: 320, height: 640 } : { width: 1280, height: 800 },
    });
    const pagina = await contexto.newPage();
    const sufijo = movil ? " (celular)" : "";
    for (const [nombre, ruta] of PUBLICAS) {
      await pagina.goto(BASE + ruta);
      await revisar(pagina, nombre + sufijo);
    }
    await reportar(pagina);
    for (const rol of movil ? ["rescatista", "adoptante"] : ROLES) await recorrerRol(pagina, rol);
    await contexto.close();
  }
}
await navegador.close();

const chrome = await chromeLauncher.launch({
  chromeFlags: ["--headless=new", "--no-sandbox"],
  chromePath: process.env.CHROME_PATH,
});
for (const [nombre, ruta] of PUBLICAS.slice(0, 4)) {
  const { lhr } = await lighthouse(BASE + ruta, {
    port: chrome.port, onlyCategories: ["accessibility"], output: "json", logLevel: "error",
  });
  const puntaje = Math.round(lhr.categories.accessibility.score * 100);
  const fallas = Object.values(lhr.audits)
    .filter((a) => a.score === 0 && a.scoreDisplayMode === "binary")
    .map((a) => ({ regla: a.id, ayuda: a.title }));
  resultados.push({ pantalla: nombre, tema: "claro", herramienta: "Lighthouse", puntaje, fallas });
}
await chrome.kill();

writeFileSync(new URL("./informe.json", import.meta.url), JSON.stringify(resultados, null, 2));
let errores = 0;
for (const r of resultados) {
  const extra = r.puntaje !== undefined ? ` · puntaje ${r.puntaje}` : "";
  const mal = r.fallas.length > 0 || (r.puntaje !== undefined && r.puntaje < PUNTAJE_MINIMO);
  if (mal) errores++;
  console.log(`${mal ? "FALLA" : "ok   "} ${r.herramienta} · ${r.pantalla} · ${r.tema}${extra}`);
  for (const f of r.fallas) console.log(`        - ${f.regla}: ${f.ayuda} ${f.nodos?.join(" | ") ?? ""}`);
}
console.log(`\n${resultados.length} revisiones, ${errores} con fallas.`);
process.exit(errores ? 1 : 0);
