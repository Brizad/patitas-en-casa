// #498: «Simular recorrido» de principio a fin, en un solo navegador con dos pestañas: el panel
// del rescatista de demostración y la consulta del ciudadano. El servidor mueve la posición
// 1,5 km hasta el animal en ~90 s; la consulta lo ve acercarse, dice «¡Está llegando!» y, al
// marcarse atendido, el mapa desaparece y vuelve la ilustración.
import { expect, test } from "@playwright/test";

const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const ANIMAL = { latitud: 7.8939, longitud: -72.5078 };

test.beforeAll(() => {
  if (!CLAVE) throw new Error("Falta PATITAS_DEMO_CONTRASENA (ver docs/aprende/e2e.md).");
});

async function token(request, usuario) {
  const r = await request.post("/auth/token", {
    form: { username: `${usuario}@demo.patitas.co`, password: CLAVE } });
  expect(r.status()).toBe(200);
  return { Authorization: `Bearer ${(await r.json()).access_token}` };
}

test("recorrido de demostración: el ciudadano ve al rescatista acercarse y llegar", async ({ browser, request }) => {
  test.setTimeout(200_000);
  // Reporte con GPS, confirmado crítico y aceptado por el rescatista de demostración.
  const { codigo } = await (await request.post("/reportes", { data: {
    descripcion: "Perro atropellado frente al parque, sangra y no se puede levantar", ...ANIMAL } })).json();
  const vet = await token(request, "veterinaria");
  expect((await request.post(`/reportes/${codigo}/confirmacion`, { headers: vet,
    data: { prioridad: "critica", justificacion: "Sangra y no se puede levantar" } })).status()).toBe(200);
  const resc = await token(request, "rescatista");
  await request.put("/rescatistas/yo/disponibilidad", { headers: resc, data: { disponible: true } });
  expect((await request.post(`/rescates/${codigo}/aceptar`, { headers: resc })).status()).toBe(200);

  const contexto = await browser.newContext();
  const panel = await contexto.newPage();
  await panel.goto("/panel/");
  await panel.getByLabel("Correo").fill("rescatista@demo.patitas.co");
  await panel.getByLabel("Contraseña").fill(CLAVE);
  await panel.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(panel.getByRole("heading", { name: `Mi rescate ${codigo}` })).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Compartir mi ubicación mientras voy en camino" })).toBeVisible();
  await panel.getByRole("button", { name: "Simular recorrido" }).click();
  await expect(panel.getByRole("status")).toContainText("Recorrido de demostración en marcha");

  const ciudadano = await contexto.newPage();
  await ciudadano.setViewportSize({ width: 390, height: 844 });
  await ciudadano.goto(`/app/#estado/${codigo}`);
  const mapa = ciudadano.locator("#estado-mapa");
  await expect(mapa).toBeVisible({ timeout: 20_000 });
  await expect(ciudadano.locator("#estado-ilu")).toBeHidden();
  await expect(ciudadano.locator("#mapa-demo")).toHaveText("Recorrido de demostración");
  const franja = ciudadano.locator("#mapa-franja");
  await expect(franja).toHaveText(/^A [\d,]+ (km|m) · llega en unos \d+ min \(aprox\.\)$/, { timeout: 30_000 });
  await expect(ciudadano.locator(".marca-animal")).toBeVisible();
  await expect(ciudadano.locator(".marca-rescatista")).toBeVisible();
  await expect(ciudadano.locator(".nombre-rescatista")).toHaveText("Rita"); // solo el nombre de pila

  await expect(franja).toHaveText("¡Está llegando!", { timeout: 110_000 });
  // Al marcarse atendido, el mapa se va y vuelve la ilustración (sin marco).
  await expect(mapa).toBeHidden({ timeout: 40_000 });
  await expect(ciudadano.locator("#estado-ilu")).toBeVisible();
  await expect(ciudadano.locator("#res-pasos li").nth(3)).toContainText("Atendido");
  await expect(panel.getByRole("heading", { name: `Mi rescate ${codigo}` })).toHaveCount(0, { timeout: 20_000 });
  await contexto.close();
});

test("sin sesión, el servidor rechaza la simulación (401; sin cuenta de demostración, 403 en pytest)", async ({ request }) => {
  const r = await request.post("/rescates/AAAA1111/simulacion");
  expect(r.status()).toBe(401); // sin sesión
});
