// Entrada del adoptante (#482, #484): hojas en las esquinas de arriba y, abajo, la foto de los gatitos
// COMPLETA (16/9), centrada y pegada al borde inferior, de ancho min(100 %, 1200 px, 52vh × 16/9).
// Nunca tapa el contenido: si no cabe, la foto baja. Sin scroll horizontal. Decorativas y en webp.
import { expect, test } from "@playwright/test";

const caja = (loc) => loc.boundingBox();

for (const [ancho, alto, hojas] of [[1440, 900, 520], [1920, 950, 520], [390, 844, 220]]) {
  test(`${ancho}×${alto}: los gatitos completos abajo, sin tapar el contenido`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: alto });
    await page.goto("/panel/#adoptar");
    await expect(page.getByRole("heading", { name: "¡Vamos a encontrar a tu compañero!" })).toBeVisible();
    await expect(page.locator(".paisaje-franja")).toHaveAttribute("aria-hidden", "true");
    const foto = page.locator(".paisaje-franja img");
    await expect(foto).toHaveAttribute("alt", "");
    await expect.poll(() => foto.evaluate((img) => img.complete && img.naturalWidth)).toBe(1200);
    expect(await foto.evaluate((img) => img.currentSrc)).toMatch(/\.webp$/);

    const f = await caja(foto);
    expect(Math.abs(f.width - Math.min(ancho, 1200, (0.52 * alto * 16) / 9))).toBeLessThan(1.5);
    expect(Math.abs(f.height - (f.width * 9) / 16)).toBeLessThan(1.5); // 16/9: la foto entera
    expect(Math.abs(f.x + f.width / 2 - ancho / 2)).toBeLessThan(1.5); // centrada
    const fin = await caja(page.getByRole("button", { name: "Ver los animales sin cuenta" }));
    expect(f.y).toBeGreaterThanOrEqual(fin.y + fin.height); // el contenido queda encima, sin taparse
    const [largo, sobra] = await page.evaluate(() => [document.documentElement.scrollHeight,
      document.documentElement.scrollWidth - innerWidth]);
    expect(Math.abs(f.y + f.height - largo)).toBeLessThan(1.5); // pegada abajo
    expect(sobra).toBeLessThanOrEqual(0); // sin scroll horizontal
    for (const lado of ["izq", "der"]) {
      expect(Math.round((await caja(page.locator(`.paisaje-hojas--${lado}`))).width)).toBe(hojas);
    }
  });
}
