// Modo piloto de usabilidad (RNF-06, #258) en el navegador: el administrador crea un participante,
// la PWA (390 px) hace el reporte de prueba, muestra el SUS y el resultado sale en el CSV. El
// reporte de prueba no debe aparecer en la cola del veterinario.
import { expect, test } from "@playwright/test";

const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const TEXTO = "Perro atropellado frente al parque Santander de prueba, no se levanta y sangra";

async function token(request, usuario) {
  const r = await request.post("/auth/token", {
    form: { username: `${usuario}@demo.patitas.co`, password: CLAVE } });
  return { Authorization: `Bearer ${(await r.json()).access_token}` };
}

test("un participante hace la prueba en el celular y su resultado sale en el CSV", async ({
  page, request }) => {
  const admin = await token(request, "admin");
  const invitacion = await (await request.post("/admin/piloto/participantes",
    { headers: admin })).json();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(invitacion.enlace);
  await expect(page.locator("#aviso-piloto")).toBeVisible();
  expect(page.url()).not.toContain("piloto=");  // el token no queda en la barra
  await page.locator("#descripcion").fill(TEXTO);
  await page.locator("#direccion").fill("Parque Santander, Cúcuta");
  await page.getByRole("button", { name: "Enviar reporte" }).click();
  await expect(page.locator("#codigo-grande")).toBeVisible();
  await expect(page.locator("#ver-estado")).toBeHidden();
  await page.getByRole("link", { name: "Responder 10 preguntas cortas" }).click();

  await page.getByRole("button", { name: "Enviar respuestas" }).click();
  await expect(page.locator("#mensaje-sus")).toContainText("Te falta responder: 1, 2");
  const grupos = page.locator("fieldset.sus-pregunta");
  await expect(grupos).toHaveCount(10);
  for (let i = 0; i < 10; i++) {
    await grupos.nth(i).getByText(i % 2 === 0 ? "4" : "2", { exact: true }).click();
  }
  await page.getByRole("button", { name: "Enviar respuestas" }).click();
  await expect(page.locator("#mensaje-sus")).toContainText("¡Gracias por participar!");

  const csv = await (await request.get("/admin/piloto/resultados.csv", { headers: admin })).text();
  expect(csv).toMatch(new RegExp(`^${invitacion.participante},\\d+,4,2,4,2,4,2,4,2,4,2$`, "m"));
  const cola = await (await request.get("/cola", { headers: await token(request, "veterinaria") }))
    .json();
  expect(cola.map((r) => r.descripcion)).not.toContain(TEXTO);
});
