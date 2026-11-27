// Entrada del adoptante (#482): hojas en las esquinas de arriba y una franja de gatitos abajo, pegada
// al borde inferior. Nunca tapa el contenido: si la pantalla es bajita, la franja se encoge y, si no basta, baja. Sin scroll
// horizontal. Las imágenes son decorativas y salen en webp.
import { expect, test } from "@playwright/test";

const caja = (loc) => loc.boundingBox();

// [ancho, alto, alto mínimo y máximo de la franja, hojas]: hasta 46vh (34vh en el celular); si el
// contenido no deja espacio, se encoge hasta 300 px (240 px) y, si ni así cabe, baja.
const CASOS = [[1440, 1200, 552, 552, 520], [1440, 900, 300, 414, 520], [390, 844, 240, 287, 220], [1440, 600, 300, 300, 520]];
for (const [ancho, alto, minimo, maximo, hojas] of CASOS) {
  test(`${ancho}×${alto}: franja abajo sin tapar el contenido`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: alto });
    await page.goto("/panel/#adoptar");
    await expect(page.getByRole("heading", { name: "¡Vamos a encontrar a tu compañero!" })).toBeVisible();
    const franja = page.locator(".paisaje-franja");
    await expect(franja).toHaveAttribute("aria-hidden", "true");
    const foto = franja.locator("img");
    await expect(foto).toHaveAttribute("alt", "");
    await expect.poll(() => foto.evaluate((img) => img.complete && img.naturalWidth > 0)).toBe(true);
    expect(await foto.evaluate((img) => img.currentSrc)).toMatch(/\.webp$/);

    const f = await caja(franja);
    const fin = await caja(page.getByRole("button", { name: "Ver los animales sin cuenta" }));
    expect(f.height).toBeGreaterThan(minimo - 1);
    expect(f.height).toBeLessThan(maximo + 1);
    expect(f.y).toBeGreaterThanOrEqual(fin.y + fin.height); // el contenido queda encima, sin taparse
    const pagina = await page.evaluate(() => [document.documentElement.scrollHeight, innerHeight,
      document.documentElement.scrollWidth - innerWidth]);
    expect(Math.abs(f.y + f.height - pagina[0])).toBeLessThan(2); // pegada al borde inferior
    if (alto === 600) expect(pagina[0]).toBeGreaterThan(alto); // bajita: la franja baja
    else expect(pagina[0]).toBe(pagina[1]); // cabe: la franja termina justo abajo
    expect(pagina[2]).toBeLessThanOrEqual(0); // sin scroll horizontal
    for (const lado of ["izq", "der"]) {
      expect(Math.round((await caja(page.locator(`.paisaje-hojas--${lado}`))).width)).toBe(hojas);
    }
  });
}
