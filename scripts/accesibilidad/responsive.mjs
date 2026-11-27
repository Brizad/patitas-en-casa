// Revisión responsive (#250): cada pantalla de la PWA y del panel a 360, 768 y 1440 px, en modo
// claro y oscuro. Mide lo que axe no mide y guarda una captura de cada combinación.
//
// - Desplazamiento horizontal de la página.
// - Textos cortados: un elemento con overflow oculto cuyo contenido no cabe.
// - Tablas que se salen de la pantalla sin una caja con desplazamiento propio.
// - Objetivos táctiles de menos de 44 × 44 px (botones, enlaces sueltos, campos).
// - Contraste (regla color-contrast de axe-core).
//
//   PATITAS_DEMO_CONTRASENA=... node responsive.mjs [http://127.0.0.1:8010] [carpeta-capturas]
import { mkdirSync, writeFileSync } from "node:fs";
import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright-core";

const BASE = process.argv[2] ?? "http://127.0.0.1:8010";
const CARPETA = process.argv[3] ?? "capturas-responsive";
const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const ANCHOS = [360, 768, 1440];
const MINIMO_TACTIL = 44;
const ROLES = ["veterinaria", "coordinador", "rescatista", "adoptante", "admin", "alcaldia"];
if (!CLAVE) {
  console.error("Falta PATITAS_DEMO_CONTRASENA.");
  process.exit(2);
}
mkdirSync(CARPETA, { recursive: true });
const hallazgos = [];

function medir() {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
  };
  const nombre = (el) => (el.getAttribute("aria-label") || el.innerText || el.value ||
    el.getAttribute("placeholder") || el.id || el.tagName).trim().slice(0, 40);
  const conDesplazamiento = (el) => {
    for (let p = el.parentElement; p; p = p.parentElement) {
      if (["auto", "scroll"].includes(getComputedStyle(p).overflowX)) return true;
    }
    return false;
  };
  const resultado = { desborde: document.documentElement.scrollWidth - innerWidth,
    cortados: [], tablas: [], pequenos: [] };
  for (const el of document.querySelectorAll("body *")) {
    if (!visible(el)) continue;
    const s = getComputedStyle(el);
    if (["hidden", "clip"].includes(s.overflowX) && el.scrollWidth > el.clientWidth + 1
        && el.innerText.trim()) resultado.cortados.push(nombre(el));
  }
  for (const t of document.querySelectorAll("table")) {
    if (visible(t) && t.getBoundingClientRect().right > innerWidth + 1 && !conDesplazamiento(t)) {
      resultado.tablas.push(t.getAttribute("aria-label") || t.caption?.innerText || "tabla");
    }
  }
  const tactiles = "button, a[href], input:not([type=hidden]), select, textarea, summary, " +
    "[role=button], [tabindex='0']";
  for (const el of document.querySelectorAll(tactiles)) {
    if (!visible(el)) continue;
    // WCAG 2.5.8: un enlace dentro de un párrafo de texto es una excepción.
    if (el.tagName === "A" && el.closest("p, li, td, figcaption, blockquote")) continue;
    if (el.matches("input[type=checkbox], input[type=radio]") && el.closest("label")) {
      const r = el.closest("label").getBoundingClientRect();  // el objetivo es la etiqueta
      if (r.height >= 44 && r.width >= 44) continue;
    }
    if (el.matches("[tabindex='0']") && el.matches("[role=region], .ds-tabla-caja")) continue;
    const r = el.getBoundingClientRect();
    if (r.height < 44 || r.width < 44) {
      resultado.pequenos.push(`${nombre(el)} (${Math.round(r.width)}×${Math.round(r.height)})`);
    }
  }
  return resultado;
}

async function revisar(pagina, pantalla, ancho, tema) {
  await pagina.waitForLoadState("networkidle");
  await pagina.waitForTimeout(600);
  const m = await pagina.evaluate(medir);
  const { violations } = await new AxeBuilder({ page: pagina })
    .withRules(["color-contrast"]).analyze();
  const archivo = `${pantalla.replace(/[^\p{L}\p{N}]+/gu, "-")}-${ancho}-${tema}.jpg`
    .toLowerCase();
  await pagina.screenshot({ path: `${CARPETA}/${archivo}`, type: "jpeg", quality: 60,
    fullPage: true });
  hallazgos.push({ pantalla, ancho, tema, captura: archivo, desborde: m.desborde,
    cortados: [...new Set(m.cortados)], tablas: m.tablas, pequenos: [...new Set(m.pequenos)],
    contraste: violations.flatMap((v) => v.nodes.map((n) => n.target.join(" "))) });
}

async function entrar(pagina, usuario) {
  // #486: el adoptante entra por su propia puerta. about:blank antes: si solo cambiara el #,
  // la página no se recargaría y seguiría abierta la sesión anterior.
  await pagina.goto("about:blank");
  await pagina.goto(`${BASE}/panel/${usuario === "adoptante" ? "#adoptar/entrar" : ""}`);
  await pagina.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await pagina.getByLabel("Contraseña").fill(CLAVE);
  await pagina.getByRole("button", { name: "Entrar" }).click();
  await pagina.getByRole("button", { name: "Salir" }).waitFor();
}

const navegador = await chromium.launch({ channel: process.env.A11Y_CANAL ?? "chrome" });
for (const tema of ["light", "dark"]) {
  for (const ancho of ANCHOS) {
    const contexto = await navegador.newContext({ colorScheme: tema, locale: "es-CO",
      serviceWorkers: "block", viewport: { width: ancho, height: 900 } });
    const p = await contexto.newPage();
    for (const [nombre, ruta] of [["inicio", "/"], ["pwa-reportar", "/app/#reportar"],
      ["pwa-consultar", "/app/#estado"], ["panel-entrar", "/panel/"],
      ["panel-registro", "/panel/#registro"]]) {
      await p.goto(BASE + ruta);
      await revisar(p, nombre, ancho, tema);
    }
    // Errores visibles: enviar el reporte vacío y entrar con una clave equivocada.
    await p.goto(`${BASE}/app/#reportar`);
    await p.locator("#paso-siguiente").click(); // #428: «Siguiente» con el paso 1 vacío
    await revisar(p, "pwa-reportar-errores", ancho, tema);
    await p.goto(`${BASE}/panel/`);
    await p.getByLabel("Correo").fill("nadie@demo.patitas.co");
    await p.getByLabel("Contraseña").fill("una-clave-equivocada");
    await p.getByRole("button", { name: "Entrar" }).click();
    await p.waitForTimeout(800);
    await revisar(p, "panel-entrar-error", ancho, tema);
    for (const rol of ROLES) {
      await entrar(p, rol);
      const pestanas = p.locator('nav[aria-label="Secciones"] button');
      const total = Math.max(await pestanas.count(), 1);
      for (let i = 0; i < total; i++) {
        let nombre = rol;
        if (await pestanas.count()) {
          nombre = `${rol}-${await pestanas.nth(i).innerText()}`;
          await pestanas.nth(i).click();
        }
        await revisar(p, nombre, ancho, tema);
        if (nombre.endsWith("Cola de triaje") && rol === "veterinaria") {
          await p.locator("button.item").first().click();
          await revisar(p, `${rol}-reporte-abierto`, ancho, tema);
        }
      }
      await p.getByRole("button", { name: "Salir" }).click();
    }
    await contexto.close();
  }
}
await navegador.close();
writeFileSync(`${CARPETA}/hallazgos.json`, JSON.stringify(hallazgos, null, 2));
const conProblema = hallazgos.filter((h) => h.desborde > 0 || h.cortados.length
  || h.tablas.length || h.pequenos.length || h.contraste.length);
console.log(`${hallazgos.length} combinaciones revisadas; ${conProblema.length} con algo que ver.`);
for (const h of conProblema) {
  console.log(`- ${h.pantalla} · ${h.ancho} · ${h.tema}: desborde ${h.desborde} · cortados ` +
    `${h.cortados.length} · tablas ${h.tablas.length} · pequeños ${h.pequenos.length} · ` +
    `contraste ${h.contraste.length}`);
}
