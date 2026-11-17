// PWA del ciudadano en un celular de 360 px: qué hacer mientras llega ayuda (H-1), el aviso de
// «sin conexión» solo sin señal (H-2) y el aviso de arranque en frío de Render.
// Corre después de aspecto, flujo y piloto (orden alfabético): crea un reporte de más.
import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 360, height: 800 } });

test("H-2: el aviso de «sin conexión» solo aparece cuando no hay señal", async ({ page, context }) => {
  await page.goto("/app/#reportar");
  const aviso = page.locator("#aviso-sin-conexion");
  await expect(aviso).toBeHidden();
  await context.setOffline(true);
  await expect(aviso).toBeVisible();
  await expect(aviso).toContainText("se envía solo al volver la señal");
  await context.setOffline(false);
  await expect(aviso).toBeHidden();
});

test("H-1: «¡Gracias por avisar!» dice qué hacer mientras llega ayuda, sin la prioridad (RN-14)", async ({ page }) => {
  await page.goto("/app/");
  await page.locator("#descripcion").fill("Perro atropellado convulsionando en la avenida, sangra mucho");
  await page.locator("#direccion").fill("Avenida Libertadores con calle 10, Cúcuta");
  await page.getByRole("button", { name: "Enviar reporte" }).click();
  await expect(page.getByRole("heading", { name: "¡Gracias por avisar!" })).toBeVisible();
  const consejos = page.locator("#mientras-llega");
  await expect(consejos.getByRole("heading", { name: "Mientras llega ayuda" })).toBeVisible();
  await expect(consejos.getByRole("listitem")).toHaveCount(3);
  // Un reporte que el triaje ve crítico: aun así la pantalla no deja ver la prioridad.
  const texto = (await page.locator("#pantalla-codigo").innerText()).toLowerCase();
  for (const palabra of ["prioridad", "crítica", "critica", "urgente"]) expect(texto).not.toContain(palabra);
  const ancho = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(ancho).toBeLessThanOrEqual(360);
});

test("si el servidor tarda en responder, la PWA avisa que está despertando", async ({ page }) => {
  await page.route("**/reportes/*/seguimiento", async (ruta) => {
    await new Promise((listo) => setTimeout(listo, 5500)); // Render dormido
    await ruta.continue();
  });
  await page.goto("/app/#estado");
  await page.locator("#codigo").fill("ZZZZ9999");
  await page.locator("#consulta button").click();
  await expect(page.locator("#mensaje")).toContainText("El servidor está despertando", { timeout: 8000 });
  await expect(page.locator("#mensaje")).toContainText("No encontramos el código ZZZZ9999", { timeout: 10000 });
});
