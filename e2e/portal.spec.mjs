// #486: cada puerta deja entrar solo a su rol. Con la contraseña correcta en la puerta equivocada,
// el servidor no entrega token (403) y la pantalla enlaza a la puerta correcta.
import { expect, test } from "@playwright/test";

const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;

test.beforeAll(() => {
  if (!CLAVE) throw new Error("Falta PATITAS_DEMO_CONTRASENA (ver docs/aprende/e2e.md).");
});

async function intentar(page, ruta, usuario) {
  await page.goto(ruta);
  await page.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await page.getByLabel("Contraseña").fill(CLAVE);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
}

test("la cuenta de adoptante no entra por la puerta del personal", async ({ page }) => {
  const respuesta = page.waitForResponse((r) => r.url().endsWith("/auth/token"));
  await intentar(page, "/panel/", "adoptante");
  expect((await respuesta).status()).toBe(403);
  await expect(page.getByRole("alert")).toContainText("Esta cuenta es de adoptante. Entra por «Adoptar».");
  await expect(page.getByRole("button", { name: "Salir" })).toHaveCount(0);
  await page.getByRole("button", { name: "Ir a «Adoptar»" }).click();
  await expect(page).toHaveURL(/#adoptar$/);
});

test("la cuenta del personal no entra por la puerta del adoptante", async ({ page }) => {
  await intentar(page, "/panel/#adoptar/entrar", "veterinaria");
  await expect(page.getByRole("alert")).toContainText("Esta cuenta es del personal del refugio.");
  await expect(page.getByRole("button", { name: "Salir" })).toHaveCount(0);
  await page.getByRole("button", { name: "Ir a «¿Trabajas en el refugio?»" }).click();
  await expect(page.getByRole("heading", { name: "Entrar como personal del refugio" })).toBeVisible();
});

test("el servidor no entrega token con el portal equivocado", async ({ request }) => {
  for (const [usuario, portal] of [["veterinaria", "adoptante"], ["adoptante", "personal"]]) {
    const r = await request.post("/auth/token", {
      form: { username: `${usuario}@demo.patitas.co`, password: CLAVE, portal } });
    expect(r.status()).toBe(403);
    expect(await r.json()).not.toHaveProperty("access_token");
  }
});
