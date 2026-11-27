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

// #488: «Entrar como adoptante» y «Crear mi cuenta de adoptante» mantienen el mismo fondo (sin manchas):
// la misma foto, que no se recarga al cambiar de pantalla, y siempre debajo del formulario.
for (const [ancho, alto] of [[1440, 900], [390, 844]]) {
  test(`${ancho}×${alto}: «Entrar» y «Crear» con el mismo fondo, sin recargar la foto`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: alto });
    await page.goto("/panel/#adoptar");
    const foto = page.locator(".paisaje-franja img");
    await expect.poll(() => foto.evaluate((img) => img.complete && img.naturalWidth)).toBe(1200);
    await foto.evaluate((img) => { img.dataset.misma = "si"; }); // marca: si se vuelve a montar, se pierde
    for (const [boton, titulo, ultimo] of [
      ["Ya tengo cuenta", "Entrar como adoptante", "Volver"],
      ["Soy nuevo: crear cuenta", "Crear mi cuenta de adoptante", "Volver"]]) {
      await page.getByRole("button", { name: boton }).click();
      await expect(page.getByRole("heading", { name: titulo })).toBeVisible();
      await expect(foto).toHaveAttribute("data-misma", "si");
      await expect(page.locator(".adop-fondo")).toBeHidden(); // sin las manchas de colores
      await expect(page.locator(".paisaje-hojas--izq")).toBeVisible();
      const f = await caja(foto);
      const fin = await caja(page.getByRole("button", { name: ultimo }));
      expect(f.y).toBeGreaterThanOrEqual(fin.y + fin.height); // la foto nunca tapa el formulario
      expect(Math.abs(f.height - (f.width * 9) / 16)).toBeLessThan(1.5); // completa
      expect(f.width).toBeLessThanOrEqual(1200);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    }
    await expect(page.getByText("Ley 1581 de 2012")).toBeVisible();
  });
}
