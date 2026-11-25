// Flujo completo de un rescate en el navegador (#233), sobre una instancia real: API + PostgreSQL
// + panel compilado + PWA, con los datos de demostración (cuentas *@demo.patitas.co).
// Ciudadano (390 px) → veterinario confirma crítica → rescatista acepta, llega y traslada →
// coordinador registra el ingreso con el código → historial y «Mis rescates» → seguimiento.
import { expect, test } from "@playwright/test";

const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const TELEFONO = { width: 390, height: 844 };
const DESCRIPCION = "Perro atropellado convulsionando en la avenida, sangra mucho y no responde";
const JUSTIFICACION = "Convulsiona y sangra: riesgo de muerte inmediato";

test.describe.configure({ mode: "serial" }); // cada paso usa el código del anterior
let codigo = "";

test.beforeAll(() => {
  if (!CLAVE) throw new Error("Falta PATITAS_DEMO_CONTRASENA (ver docs/aprende/e2e.md).");
});

async function entrar(page, usuario) {
  await page.goto("/panel/");
  await page.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await page.getByLabel("Contraseña").fill(CLAVE);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("button", { name: "Salir" })).toBeVisible();
}

async function token(request, usuario) {
  const r = await request.post("/auth/token", {
    form: { username: `${usuario}@demo.patitas.co`, password: CLAVE } });
  expect(r.status()).toBe(200);
  return (await r.json()).access_token;
}

async function sinScrollHorizontal(page) {
  const ancho = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(ancho).toBeLessThanOrEqual(TELEFONO.width);
}

test("el ciudadano no puede enviar una descripción sin sentido (RN-01)", async ({ page }) => {
  await page.setViewportSize(TELEFONO);
  await page.goto("/app/#reportar");
  await page.locator("#descripcion").fill("Jsjsisoslqmwnabsnsnans Eksowpwpwowowowlwkksksks");
  await page.getByRole("button", { name: "Siguiente" }).click(); // #428: el paso 1 valida
  await expect(page.locator("#error-descripcion"))
    .toHaveText("Describe con palabras qué le pasa al animal.");
  await expect(page.locator("#codigo-grande")).toBeHidden();
});

test("el ciudadano reporta desde el teléfono y recibe su código", async ({ page }) => {
  await page.setViewportSize(TELEFONO);
  await page.goto("/app/#reportar");
  await page.locator("#descripcion").fill(DESCRIPCION);
  await page.getByRole("button", { name: "Siguiente" }).click(); // #428: 4 pasos
  await page.locator("#direccion").fill("Avenida Libertadores con calle 10, Cúcuta");
  await page.getByRole("button", { name: "Comuna 5" }).click();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await page.getByRole("button", { name: "Saltar este paso" }).click();
  await sinScrollHorizontal(page);
  await page.getByRole("button", { name: "Enviar reporte" }).click();
  await expect(page.locator("#codigo-grande")).toBeVisible();
  codigo = (await page.locator("#codigo-grande").innerText()).replace(/\s/g, "");
  expect(codigo).toMatch(/^[A-Z0-9]{8}$/);
});

test("el veterinario confirma la prioridad crítica", async ({ page }) => {
  await entrar(page, "veterinaria");
  await page.locator("button.item", { hasText: codigo }).click();
  await expect(page.getByRole("heading", { name: `Reporte ${codigo}` })).toBeVisible();
  const confirmar = page.getByRole("button", { name: "Confirmar crítica" });
  if (await confirmar.isVisible()) {
    await confirmar.click();
  } else { // el sistema sugirió otra prioridad: se ajusta con justificación (RN-16)
    await page.getByRole("button", { name: "Ajustar prioridad…" }).click();
    await page.getByLabel("Nueva prioridad").selectOption("critica");
    await page.getByLabel(/Justificación/).fill(JUSTIFICACION);
    await page.getByRole("button", { name: "Guardar ajuste" }).click();
  }
  await expect(page.locator(".ds-msg--ok", { hasText: codigo })).toBeVisible();
  await expect(page.locator("button.item", { hasText: codigo })).toHaveCount(0); // sale de la cola
});

test("un rol equivocado recibe 403 y sin sesión 401", async ({ request }) => {
  const animal = { nombre: "Intruso", especie: "perro", estado_salud: "Sin datos" };
  const sinSesion = await request.post("/refugio/ingresos", { data: animal });
  expect(sinSesion.status()).toBe(401);
  const vet = await token(request, "veterinaria"); // el ingreso es solo del coordinador
  const r = await request.post("/refugio/ingresos", {
    data: animal, headers: { Authorization: `Bearer ${vet}` } });
  expect(r.status()).toBe(403);
  const resc = await token(request, "rescatista"); // la cola es del veterinario y coordinador
  const cola = await request.get("/cola", { headers: { Authorization: `Bearer ${resc}` } });
  expect(cola.status()).toBe(403);
});

test("el rescatista acepta, llega y marca trasladado", async ({ page }) => {
  await entrar(page, "rescatista");
  const oferta = page.locator("li.oferta", { hasText: codigo });
  await expect(oferta).toBeVisible();
  await oferta.getByRole("button", { name: "Aceptar rescate" }).click();
  await expect(page.getByRole("heading", { name: `Mi rescate ${codigo}` })).toBeVisible();
  await page.getByRole("button", { name: "Llegué al sitio" }).click();
  await expect(page.getByRole("status")).toHaveText("Llegada registrada.");
  await page.getByLabel("Resultado").selectOption("trasladado");
  await page.getByRole("button", { name: "Registrar resultado" }).click();
  await expect(page.getByRole("status"))
    .toHaveText("Resultado registrado: trasladado al refugio.");
});

test("el coordinador registra el ingreso con el código del reporte", async ({ page }) => {
  await entrar(page, "coordinador");
  await page.getByLabel("Nombre").fill("Rayo");
  await page.getByLabel("Especie").selectOption("perro");
  await page.getByLabel("Estado de salud").fill("Atropellado, en observación");
  await page.getByLabel("Código del reporte (opcional)").fill(codigo);
  await page.getByRole("button", { name: "Registrar ingreso" }).click();
  await expect(page.getByRole("status")).toContainText("Ingreso de Rayo registrado");
});

test("el historial del veterinario y «Mis rescates» muestran el caso", async ({ page }) => {
  await entrar(page, "veterinaria");
  await page.getByRole("button", { name: "Historial" }).click();
  await expect(page.getByRole("region", { name: "Tabla del historial" })).toContainText(codigo);
  await page.getByRole("button", { name: "Salir" }).click();
  await entrar(page, "rescatista");
  await page.getByRole("button", { name: "Mis rescates" }).click();
  await expect(page.getByRole("region", { name: "Tabla de mis rescates" })).toContainText(codigo);
});

test("el seguimiento por código muestra los pasos y nada privado (RN-14)", async ({ page }) => {
  await page.setViewportSize(TELEFONO);
  await page.goto(`/app/#estado/${codigo}`);
  const pasos = page.locator("#res-pasos li");
  await expect(pasos).toHaveCount(5);
  await expect(pasos.nth(0)).toContainText("Recibido");
  await expect(pasos.nth(3)).toContainText("Atendido");
  await expect(pasos.nth(4)).toContainText("Cerrado");
  await expect(page.locator("body")).not.toContainText("convulsionando");
  await expect(page.locator("body")).not.toContainText("Libertadores");
  await sinScrollHorizontal(page);
});
