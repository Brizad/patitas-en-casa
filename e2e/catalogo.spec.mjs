// «Esperan un hogar» (#477): tarjetas de foto y nombre; al tocar una, el detalle se abre debajo de
// su fila (como Google Imágenes). Se cambia de animal, se cierra con Esc, con la X o con la misma
// tarjeta, y en el celular hay 2 columnas. Usa los animales publicados de la demostración (3 o más).
import { expect, test } from "@playwright/test";

const caja = (loc) => loc.boundingBox();

for (const ancho of [1440, 390]) {
  test.describe(`${ancho} px`, () => {
    test.use({ viewport: { width: ancho, height: 900 } });

    test("abrir, cambiar de animal y cerrar con Esc, la X o la misma tarjeta", async ({ page }) => {
      await page.goto("/panel/#adoptar/animales");
      const tarjetas = page.locator(".acceso-animal");
      await expect(tarjetas.nth(2)).toBeVisible({ timeout: 30_000 });
      const [primera, segunda] = [tarjetas.nth(0), tarjetas.nth(1)];
      const detalle = page.locator("#detalle-animal");
      const nombre = async (t) => (await t.locator(".acceso-nombre").textContent()).trim();
      await primera.click();
      await expect(primera).toHaveAttribute("aria-expanded", "true");
      await expect(primera).toHaveAttribute("aria-controls", "detalle-animal");
      await expect(detalle.getByRole("heading", { name: await nombre(primera) })).toBeFocused();
      await expect(detalle.getByRole("button", { name: `¡Te elijo, ${await nombre(primera)}!` })).toBeVisible();
      await expect(detalle.getByRole("button", { name: "Ver en Elige a tu compañero" })).toBeVisible();
      await expect(detalle.locator(".convive-icono")).toHaveCount(3);
      const arriba = await caja(primera);
      expect((await caja(detalle)).y).toBeGreaterThan(arriba.y + arriba.height);

      await segunda.click(); // misma fila: cambia de animal
      await expect(detalle.getByRole("heading", { name: await nombre(segunda) })).toBeVisible();
      await expect(primera).toHaveAttribute("aria-expanded", "false");
      await page.keyboard.press("Escape");
      await expect(detalle).toHaveCount(0);
      await expect(segunda).toBeFocused(); // el foco vuelve a la tarjeta

      await primera.click();
      await detalle.getByRole("button", { name: "Cerrar" }).click();
      await expect(detalle).toHaveCount(0);
      await expect(primera).toBeFocused();
      await primera.click();
      await primera.click();
      await expect(detalle).toHaveCount(0);

      if (ancho >= 560) return;
      // Celular: 2 columnas; el detalle a todo el ancho debajo de la fila tocada y la foto arriba.
      await page.mouse.move(0, 0); // sin el «hover», que sube la tarjeta 2 px
      const [a, b, c] = [await caja(primera), await caja(segunda), await caja(tarjetas.nth(2))];
      expect(Math.abs(a.y - b.y)).toBeLessThan(2);
      expect(c.y).toBeGreaterThan(a.y + a.height);
      await primera.click();
      const d = await caja(detalle);
      expect((await caja(tarjetas.nth(2))).y).toBeGreaterThan(d.y + d.height - 1); // la fila 2 baja
      expect(d.width).toBeGreaterThan(b.x + b.width - a.x - 4);
      const foto = await caja(detalle.locator(".detalle-foto"));
      expect(foto.y + foto.height).toBeLessThanOrEqual((await caja(detalle.locator("h2"))).y);
      await tarjetas.nth(2).click(); // otra fila: el detalle se va debajo de esa
      await expect(tarjetas.nth(2)).toHaveAttribute("aria-expanded", "true");
      expect((await caja(detalle)).y).toBeGreaterThan((await caja(tarjetas.nth(2))).y);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    });
  });
}
