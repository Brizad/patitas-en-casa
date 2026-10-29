// Capturas de pantalla del manual de usuario (docs/manual-usuario.md, #156).
//
// Recorre cada rol con los datos de demostración del servidor en memoria (servidor_demo.py)
// y guarda JPEG en docs/manual/. Ciudadano, rescatista y adoptante en tamaño de celular
// (usan el teléfono); el resto en pantalla de computador. Para volver a tomarlas:
//   PATITAS_DEMO_CONTRASENA=... node capturas.mjs [http://127.0.0.1:8765]
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const BASE = process.argv[2] ?? "http://127.0.0.1:8765";
const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const CARPETA = fileURLToPath(new URL("../../docs/manual/", import.meta.url));
const CELULAR = { width: 390, height: 844 };
const COMPUTADOR = { width: 1280, height: 800 };
if (!CLAVE) {
  console.error("Falta PATITAS_DEMO_CONTRASENA (la misma del servidor de demostración).");
  process.exit(2);
}
mkdirSync(CARPETA, { recursive: true });

const navegador = await chromium.launch({ channel: process.env.A11Y_CANAL ?? "chrome" });

async function pagina(tamano) {
  const contexto = await navegador.newContext({
    viewport: tamano, deviceScaleFactor: 1, colorScheme: "light", locale: "es-CO",
    serviceWorkers: "block",
  });
  return contexto.newPage();
}

async function foto(p, nombre) {
  await p.waitForLoadState("networkidle");
  await p.waitForTimeout(700);  // React pide los datos después de pintar la pestaña
  await p.screenshot({ path: `${CARPETA}${nombre}.jpg`, type: "jpeg", quality: 70 });
  console.log(`docs/manual/${nombre}.jpg`);
}

async function entrar(p, usuario) {
  await p.goto(`${BASE}/panel/`);
  await p.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await p.getByLabel("Contraseña").fill(CLAVE);
  await p.getByRole("button", { name: "Entrar" }).click();
  await p.getByRole("button", { name: "Salir" }).waitFor();
}

async function pestana(p, nombre) {
  await p.locator('nav[aria-label="Secciones"] button', { hasText: nombre }).click();
}

// Ciudadano: inicio, reporte, código y estado.
let p = await pagina(CELULAR);
await p.goto(`${BASE}/`);
await foto(p, "01-inicio");
await p.goto(`${BASE}/app/#reportar`);
await p.locator("#descripcion").fill("Perro atropellado en la avenida, no se levanta y sangra");
await p.locator("#direccion").fill("Barrio La Playa, calle 10 con avenida 5");
await p.locator("#comuna").selectOption("2");
await foto(p, "02-ciudadano-reportar");
await p.locator('#reporte button[type="submit"]').click();
await p.waitForURL(/#codigo/);
await foto(p, "03-ciudadano-codigo");
await p.locator("#ver-estado").click();
await p.locator("#resultado").waitFor();
await foto(p, "04-ciudadano-estado");
await p.context().close();

// Veterinario: cola, detalle de un reporte y fichas del refugio.
p = await pagina(COMPUTADOR);
await entrar(p, "veterinaria");
await foto(p, "05-veterinario-cola");
await p.locator("button.item").first().click();
await foto(p, "06-veterinario-reporte");
await p.getByRole("button", { name: /Ajustar prioridad/ }).click();
await foto(p, "06b-veterinario-ajustar");
// Confirmar uno deja un cambio con «antes → después» para la captura de la bitácora.
await p.getByRole("button", { name: /^Confirmar/ }).click();
await p.getByRole("status").first().waitFor();
await pestana(p, "Refugio");
await foto(p, "07-veterinario-refugio");
await p.context().close();

// Rescatista (celular).
p = await pagina(CELULAR);
await entrar(p, "rescatista");
await foto(p, "08-rescatista");
await p.context().close();

// Coordinador: refugio, adopciones e indicadores.
p = await pagina(COMPUTADOR);
await entrar(p, "coordinador");
await foto(p, "09-coordinador-refugio");
await pestana(p, "Adopciones");
await foto(p, "10-coordinador-adopciones");
await pestana(p, "Indicadores");
await foto(p, "11-coordinador-indicadores");
await p.context().close();

// Adoptante (celular): registro y su pantalla.
p = await pagina(CELULAR);
await p.goto(`${BASE}/panel/#registro`);
await foto(p, "12-adoptante-registro");
await entrar(p, "adoptante");
await foto(p, "13-adoptante");
await p.context().close();

// Administrador: cuentas y refugios, bitácora.
p = await pagina(COMPUTADOR);
await entrar(p, "admin");
await foto(p, "14-administrador");
await pestana(p, "Indicadores");
await p.getByRole("heading", { name: /Bitácora/ }).scrollIntoViewIfNeeded();
await foto(p, "15-administrador-bitacora");
await p.context().close();

// Alcaldía: solo indicadores anonimizados.
p = await pagina(COMPUTADOR);
await entrar(p, "alcaldia");
await foto(p, "16-alcaldia");
await p.context().close();

await navegador.close();
