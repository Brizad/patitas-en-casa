// #490: «Estado del reporte» con una ilustración según el estado real que devuelve el servidor. Las
// respuestas se simulan con page.route (las mismas formas que GET /reportes/{codigo}/seguimiento).
import { expect, test } from "@playwright/test";

const paso = (nombre, estado, detalle = null) => ({ nombre, estado, detalle, fecha: null });
const NOMBRES = ["Recibido", "Revisado por el veterinario", "Rescatista en camino", "Atendido", "Cerrado"];
const conActual = (i, detalle = null) => NOMBRES.map((n, j) =>
  paso(n, j < i ? "hecho" : j === i ? "actual" : "pendiente", j === i ? detalle : null));

const CASOS = [
  ["AAAA1111", conActual(1), "recibido", "Recibimos tu reporte"],
  ["BBBB2222", conActual(2, "Buscando rescatista disponible"), "revisado", "Un veterinario lo revisó"],
  ["CCCC3333", conActual(2), "rescate", "El rescate va en camino"],
  ["DDDD4444", conActual(3, "Rescatista en el sitio"), "rescate", "El rescate va en camino"],
  ["EEEE5555", NOMBRES.map((n) => paso(n, "hecho")), "cerrado", "¡Caso cerrado!"],
];

async function simular(page) {
  await page.route("**/reportes/*/seguimiento", (ruta) => {
    const codigo = ruta.request().url().split("/").at(-2);
    const caso = CASOS.find(([c]) => c === codigo);
    if (!caso) return ruta.fulfill({ status: 404, json: { detail: "No existe." } });
    return ruta.fulfill({ json: { codigo, ultimo_cambio: "2026-11-27T15:00:00Z", pasos: caso[1] } });
  });
}

async function consultar(page, codigo) {
  await page.locator("#codigo").fill(codigo);
  await page.locator("#consulta button").click();
}

const visible = (page) => page.locator("#estado-marco .estado-capa.activa .estado-foto");

for (const [ancho, alto] of [[1440, 900], [390, 844]]) {
  test(`${ancho} px: la imagen sigue el estado real y vuelve a la de espera si el código no existe`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: alto });
    await simular(page);
    await page.goto("/app/#estado");
    const marco = page.locator("#estado-marco");
    await expect(marco).toHaveAttribute("aria-hidden", "true");
    await expect(marco).toHaveAttribute("data-etapa", "espera");
    await expect(page.locator("#estado-etiqueta")).toBeHidden();
    for (const img of await marco.locator("img").all()) await expect(img).toHaveAttribute("alt", "");

    for (const [codigo, , etapa, etiqueta] of CASOS) {
      await consultar(page, codigo);
      await expect(marco).toHaveAttribute("data-etapa", etapa);
      await expect(page.locator("#estado-etiqueta")).toHaveText(etiqueta);
      await expect.poll(() => visible(page).evaluate((i) => i.complete && i.currentSrc)).toMatch(`-${etapa}.webp`);
      await expect(page.locator("#res-pasos li")).toHaveCount(5); // la línea de tiempo, igual que antes
    }
    await consultar(page, "ZZZZ9999");
    await expect(page.locator("#mensaje")).toContainText("No encontramos el código ZZZZ9999");
    await expect(marco).toHaveAttribute("data-etapa", "espera");

    // La foto se ve completa (contain) sobre la misma en cover y difuminada.
    const estilos = await page.evaluate(() => ["estado-foto", "estado-fondo"].map((c) => {
      const e = getComputedStyle(document.querySelector(`.estado-capa.activa .${c}`));
      return [e.objectFit, e.filter];
    }));
    expect(estilos[0][0]).toBe("contain");
    expect(estilos[1][0]).toBe("cover");
    expect(estilos[1][1]).toContain("blur(18px)");

    const m = await marco.boundingBox();
    const campo = await page.locator("#codigo").boundingBox();
    if (ancho >= 1024) { // dos columnas: el marco a la derecha, de 420 × 520
      expect(Math.round(m.width)).toBe(420);
      expect(Math.round(m.height)).toBe(520);
      expect(m.x).toBeGreaterThan(campo.x + campo.width);
    } else { // celular: arriba de la tarjeta, a todo el ancho y de 220 px
      await consultar(page, "AAAA1111");
      await expect(page.locator("#resultado")).toBeVisible();
      const tarjeta = await page.locator("#resultado").boundingBox();
      const arriba = await marco.boundingBox();
      expect(Math.round(m.height)).toBe(220);
      expect(Math.abs(m.width - tarjeta.width)).toBeLessThan(2); // a todo el ancho, como la tarjeta
      expect(arriba.y + arriba.height).toBeLessThanOrEqual(tarjeta.y);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  });
}

test("con «reducir movimiento» la imagen cambia sin fundido", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await simular(page);
  await page.goto("/app/#estado");
  const transicion = await page.locator(".estado-capa").first().evaluate((e) => getComputedStyle(e).transitionDuration);
  expect(transicion).toBe("0s");
});
