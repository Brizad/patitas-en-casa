// #516: «Mi hogar» renovado con las respuestas REALES guardadas (servidor simulado con page.route).
import { expect, test } from "@playwright/test";

const PERFIL = { vivienda: "apartamento", tiene_patio: true, hay_ninos: true, otros_animales: true,
  horas_solo_al_dia: 5, experiencia: true, acepta_seguimiento: true };

async function entrar(page, perfil) {
  await page.route("**/auth/token", (r) => r.fulfill({ json: { access_token: "x", token_type: "bearer" } }));
  await page.route("**/auth/yo", (r) => r.fulfill({ json: { correo: "a@correo.co", nombre: "Ana", rol: "adoptante" } }));
  await page.route("**/adoptantes/yo/perfil", (r) => r.fulfill({ json: perfil }));
  await page.route("**/adopciones/solicitudes/mias", (r) => r.fulfill({ json: [] }));
  await page.route("**/adopciones/animales", (r) => r.fulfill({ json: [] }));
  await page.route("**/adopciones/coleccion", (r) => r.fulfill({ json: { esperando: 0, adoptados_total: 0, adoptados: [] } }));
  await page.route("**/adopciones/recomendaciones", (r) => r.fulfill({ json: [] }));
  await page.goto("/panel/");
  await page.getByLabel("Correo").fill("a@correo.co");
  await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.getByRole("button", { name: "Mi hogar", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Así es tu hogar" })).toBeVisible();
}

for (const ancho of [1440, 390]) {
  test.describe(`${ancho} px`, () => {
    test.use({ viewport: { width: ancho, height: 900 } });

    test("acepta el seguimiento: listo para adoptar y sus 7 respuestas reales", async ({ page }) => {
      await entrar(page, PERFIL);
      await expect(page.locator(".mihogar-estado")).toHaveText("Listo para adoptar");
      await expect(page.locator(".mihogar-aviso")).toHaveCount(0);
      const tarjetas = page.locator(".mihogar-respuestas > li");
      await expect(tarjetas).toHaveCount(7);
      await expect(page.locator(".mihogar-respuesta")).toHaveText(["Apartamento", "Sí, hay patio", "Sí, hay niños",
        "Sí, ya tengo", "Medio día (5 h)", "Sí, ya he cuidado", "Sí, acepto"]);
      await expect(tarjetas.last()).toHaveClass(/ancha/);
      await expect(tarjetas.last()).not.toHaveClass(/alerta/);
      await page.getByRole("button", { name: "Cambiar: ¿Hay niños en casa?" }).click();
      await expect(page.getByRole("heading", { name: /¿Hay niños en casa\?/ })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    });

    test("no acepta: falta el seguimiento, aviso y «Cambiar esta respuesta» va directo a esa pregunta", async ({ page }) => {
      await entrar(page, { ...PERFIL, acepta_seguimiento: false });
      await expect(page.locator(".mihogar-estado")).toHaveText("Falta aceptar el seguimiento");
      await expect(page.locator(".mihogar-respuestas > li").last()).toHaveClass(/alerta/);
      await expect(page.locator(".mihogar-respuesta").last()).toHaveText("Ahora no");
      await page.getByRole("button", { name: "Cambiar esta respuesta" }).click();
      await expect(page.locator(".adop-contador")).toHaveText("9 de 9");
    });
  });
}
