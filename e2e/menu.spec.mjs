// Menú fijo de la página de inicio (#462): al bajar, la barra sigue visible arriba y se compacta;
// en el celular, el botón de tres rayas despliega los enlaces y se cierra al tocar uno.
import { expect, test } from "@playwright/test";

for (const ancho of [1440, 390]) {
  test.describe(`${ancho} px`, () => {
    test.use({ viewport: { width: ancho, height: 844 } });

    test("la barra sigue visible arriba después de bajar la página", async ({ page }) => {
      await page.goto("/");
      const barra = page.locator("header.nav");
      await page.mouse.wheel(0, 3000);
      await expect(barra).toHaveClass(/compacta/);
      await expect(barra).toBeInViewport();
      const caja = await barra.boundingBox();
      expect(Math.abs(caja.y)).toBeLessThanOrEqual(1);
      await expect(barra.getByRole("link", { name: "Reportar" })).toBeVisible();
    });

    if (ancho < 760) {
      test("el menú del celular se abre con el botón y se cierra al tocar un enlace", async ({ page }) => {
        await page.goto("/");
        const boton = page.getByRole("button", { name: "Abrir el menú" });
        await expect(boton).toHaveAttribute("aria-expanded", "false");
        await boton.click();
        await expect(page.locator(".nav-menu")).toHaveAttribute("aria-expanded", "true");
        await page.locator("#menu-principal").getByRole("link", { name: "Cómo funciona" }).click();
        await expect(page.locator(".nav-menu")).toHaveAttribute("aria-expanded", "false");
        await expect(page.locator("#titulo-ayuda")).toBeInViewport();
      });
    }
  });
}
