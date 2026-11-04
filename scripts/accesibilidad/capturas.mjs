// Capturas de pantalla del manual de usuario (docs/manual-usuario.md, #156).
//
// Recorre cada rol con los datos de demostración y guarda JPEG en docs/manual/. Con la instancia
// de PostgreSQL de docs/aprende/e2e.md (puerto 8010) salen también el video y los historiales;
// con el servidor en memoria (servidor_demo.py) las pantallas sin video. Ciudadano, rescatista y adoptante en tamaño de celular
// (usan el teléfono); el resto en pantalla de computador. Para volver a tomarlas:
//   PATITAS_DEMO_CONTRASENA=... node capturas.mjs [http://127.0.0.1:8765]
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const BASE = process.argv[2] ?? "http://127.0.0.1:8010";
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

async function foto(p, nombre, { completa = false } = {}) {
  await p.waitForLoadState("networkidle");
  await p.waitForTimeout(700);  // React pide los datos después de pintar la pestaña
  await p.screenshot({ path: `${CARPETA}${nombre}.jpg`, type: "jpeg", quality: 70,
    fullPage: completa });
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

// Veterinario: cola, reporte con análisis de video y vista previa, ajuste, historial y refugio.
// Para el video hace falta un reporte con video analizado (ver docs/aprende/e2e.md).
p = await pagina(COMPUTADOR);
await entrar(p, "veterinaria");
await foto(p, "05-veterinario-cola");
const conVideo = p.locator("button.item", { hasText: process.env.CAPTURA_VIDEO ?? "camina raro" });
await (await conVideo.count() ? conVideo.first() : p.locator("button.item").first()).click();
await foto(p, "06-veterinario-reporte");
if (await p.locator(".video").count()) {
  await p.locator(".video").scrollIntoViewIfNeeded();
  await p.locator("video").first().evaluate((v) => new Promise((listo) => {
    if (v.readyState >= 2) return listo();  // primer cuadro listo para la foto
    v.addEventListener("loadeddata", () => listo(), { once: true });
  })).catch(() => {});
  await foto(p, "06c-veterinario-video", { completa: false });
}
await p.locator("button.item").first().click();
await p.getByRole("button", { name: /Ajustar prioridad/ }).click();
await foto(p, "06b-veterinario-ajustar");
// Confirmar uno deja un cambio con «antes → después» para la bitácora y una fila en el historial.
await p.getByRole("button", { name: /^Confirmar/ }).click();
await p.getByRole("status").first().waitFor();
await pestana(p, "Historial");
await foto(p, "07-veterinario-historial");
await pestana(p, "Refugio");
await foto(p, "07b-veterinario-refugio");
await p.context().close();

// Rescatista (celular): ofertas, rescate en curso y «Mis rescates».
p = await pagina(CELULAR);
await entrar(p, "rescatista");
await foto(p, "08-rescatista", { completa: true });
const oferta = p.locator("li.oferta").first();
if (await oferta.count()) {
  await oferta.getByRole("button", { name: "Aceptar rescate" }).click();
  await p.getByRole("button", { name: "Llegué al sitio" }).click();
  await p.getByRole("status").first().waitFor();
  await foto(p, "08b-rescatista-en-curso", { completa: true });
  await p.getByLabel("Resultado").selectOption("trasladado");
  await p.getByRole("button", { name: "Registrar resultado" }).click();
  await p.getByRole("status").first().waitFor();
}
await pestana(p, "Mis rescates");
await foto(p, "08c-rescatista-mis-rescates");
// El código del rescate más reciente: el coordinador lo escribe al registrar el ingreso.
const codigoRescatado = await p.locator("tbody tr code").first().innerText().catch(() => "");
await p.context().close();

// Coordinador: refugio, adopciones e indicadores.
p = await pagina(COMPUTADOR);
await entrar(p, "coordinador");
await p.getByLabel("Nombre").fill("Rayo");
await p.getByLabel("Estado de salud").fill("Atropellado, en observación");
await p.getByLabel("Código del reporte (opcional)").fill(codigoRescatado);
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
