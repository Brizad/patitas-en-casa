// Pie de la portada (#479): franja «Instalar la app» encima de las columnas, con QR y el perrito
// que sobresale a su derecha (solo en computador). «Instalar la app» usa beforeinstallprompt si el
// navegador lo ofrece, en iPhone muestra los pasos y, si no, lleva a /app/#instalar.
import { expect, test } from "@playwright/test";

const caja = (loc) => loc.boundingBox();

test.describe("1440 px", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("franja con QR a la izquierda del perrito, que sobresale del pie", async ({ page }) => {
    await page.goto("/");
    const franja = page.locator(".franja-app");
    await franja.scrollIntoViewIfNeeded();
    await expect(franja.getByText("Lleva Patitas en tu celular")).toBeVisible();
    await expect(franja.locator(".franja-qr img")).toBeVisible();
    const [f, perro, pie, columnas] = [await caja(franja), await caja(page.locator(".pie-perro")),
      await caja(page.locator(".pie")), await caja(page.locator(".pie-marca"))];
    expect(perro.y).toBeLessThan(pie.y - 40); // sobresale por encima del borde del pie
    expect(f.x + f.width).toBeLessThan(perro.x); // la franja no lo tapa
    expect(f.y + f.height).toBeLessThan(columnas.y); // y va encima de las columnas (sin redondeos)
  });

  test("con beforeinstallprompt, el clic abre la ventana de instalar", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => {
      const e = new Event("beforeinstallprompt", { cancelable: true });
      e.prompt = () => { window.pedidoInstalar = true; };
      window.dispatchEvent(e);
    });
    await page.locator(".franja-boton").click();
    expect(await page.evaluate(() => window.pedidoInstalar)).toBe(true);
    await expect(page).toHaveURL(/\/$/);
  });

  test("sin aviso del navegador, lleva a /app/#instalar", async ({ page }) => {
    await page.goto("/");
    await page.locator(".pie-enlaces [data-instalar]").click();
    await expect(page).toHaveURL(/\/app\/#instalar$/);
  });
});

test.describe("390 px", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true,
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1" });

  test("franja apilada sin QR ni perrito; en iPhone muestra los pasos", async ({ page }) => {
    await page.goto("/");
    const franja = page.locator(".franja-app");
    await franja.scrollIntoViewIfNeeded();
    await expect(page.locator(".franja-qr")).toBeHidden();
    await expect(page.locator(".pie-perro")).toBeHidden();
    const [f, boton, icono] = [await caja(franja), await caja(page.locator(".franja-boton")),
      await caja(page.locator(".franja-icono"))];
    expect(boton.width).toBeGreaterThan(f.width - 50); // a todo el ancho
    expect(boton.y).toBeGreaterThan(icono.y + icono.height); // debajo del ícono y el texto
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    await page.locator(".franja-boton").click();
    const pasos = page.locator("#instalar-iphone");
    await expect(pasos).toBeVisible();
    await expect(pasos.getByText("«Agregar a pantalla de inicio»")).toBeVisible();
    await pasos.getByRole("button", { name: "Cerrar" }).click();
    await expect(pasos).toBeHidden();
    await expect(page).toHaveURL(/\/$/);
  });
});
