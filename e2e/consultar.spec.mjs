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

const visible = (page) => page.locator("#estado-ilu img");

for (const [ancho, alto] of [[1440, 900], [390, 844]]) {
  test(`${ancho} px: la imagen sigue el estado real y vuelve a la de espera si el código no existe`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: alto });
    await simular(page);
    await page.goto("/app/#estado");
    const marco = page.locator("#estado-ilu");
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

    // #494: sin marco; la foto completa con su proporción real y los 4 bordes fundidos en el crema.
    const estilo = await visible(page).evaluate((i) => {
      const e = getComputedStyle(i);
      const f = getComputedStyle(i.closest("figure"));
      return { mascara: e.maskImage || e.webkitMaskImage, borde: f.borderTopWidth, sombra: f.boxShadow,
        fondo: f.backgroundColor, proporcion: i.width / i.height, real: i.naturalWidth / i.naturalHeight,
        ancho: i.width, natural: i.naturalWidth };
    });
    expect(estilo.mascara.match(/linear-gradient/g)).toHaveLength(2);
    expect([estilo.borde, estilo.sombra, estilo.fondo]).toEqual(["0px", "none", "rgba(0, 0, 0, 0)"]);
    expect(Math.abs(estilo.proporcion - estilo.real)).toBeLessThan(0.01); // completa, sin recortes
    expect(estilo.ancho).toBeLessThanOrEqual(estilo.natural); // nunca agrandada

    await consultar(page, "DDDD4444"); // la más alta (680 × 1024)
    await expect.poll(() => visible(page).evaluate((i) => i.complete && i.currentSrc)).toMatch("-rescate.webp");
    await expect(visible(page)).not.toHaveClass(/fuera/);
    const f = await visible(page).boundingBox();
    const etq = await page.locator("#estado-etiqueta").boundingBox();
    expect(Math.round(f.height)).toBe(ancho >= 1024 ? 540 : 300);
    expect(etq.y).toBeLessThan(f.y + f.height); // montada sobre el borde de abajo de la foto
    expect(Math.abs(etq.x + etq.width / 2 - (f.x + f.width / 2))).toBeLessThan(2); // centrada
    if (ancho >= 1024) { // a la derecha del formulario, centrada en su columna de 520 px
      const campo = await page.locator("#codigo").boundingBox();
      const columna = await marco.boundingBox();
      expect(Math.round(columna.width)).toBe(520);
      expect(f.x).toBeGreaterThan(campo.x + campo.width);
      expect(Math.abs(f.x + f.width / 2 - (columna.x + columna.width / 2))).toBeLessThan(2);
    } else { // celular: arriba de todo, centrada
      const titulo = await page.getByRole("heading", { name: "Estado del reporte" }).boundingBox();
      expect(etq.y + etq.height).toBeLessThanOrEqual(titulo.y);
      expect(Math.abs(f.x + f.width / 2 - ancho / 2)).toBeLessThan(2);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  });
}

test("con «reducir movimiento» la imagen cambia sin fundido", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await simular(page);
  await page.goto("/app/#estado");
  const transicion = await page.locator("#estado-ilu img").evaluate((e) => getComputedStyle(e).transitionDuration);
  expect(transicion).toBe("0s");
});

// #500: si la consulta responde antes de que cargue Leaflet (scripts diferidos), el mapa del
// rescate aparece igual al terminar de cargar la página, sin esperar el sondeo de 12 s.
test("el mapa del rescate aparece aunque Leaflet cargue después de la respuesta", async ({ page }) => {
  const pasos = ["Recibido", "Revisado por el veterinario", "Rescatista en camino", "Atendido", "Cerrado"]
    .map((nombre, j) => ({ nombre, estado: j < 2 ? "hecho" : j === 2 ? "actual" : "pendiente", detalle: null,
      fecha: j < 2 ? "2026-11-27T20:00:00Z" : null }));
  await page.route("**/reportes/*/seguimiento", (r) => r.fulfill({ json: { codigo: "EEEE5555",
    ultimo_cambio: "2026-11-27T20:10:00Z", nivel: "urgente", pasos, rescatista: { nombre: "Rita", simulada: false,
      animal: { latitud: 7.8939, longitud: -72.5078 }, ubicacion: { latitud: 7.9047, longitud: -72.5078 },
      distancia_m: 1200, minutos: 3 } } }));
  await page.route("**/vendor/leaflet/leaflet.js", async (r) => {
    await new Promise((listo) => setTimeout(listo, 2500));
    await r.continue();
  });
  await page.goto("/app/#estado/EEEE5555");
  await expect(page.locator("#mapa-franja")).toHaveText("A 1,2 km · llega en unos 3 min (aprox.)");
  await expect(page.locator("#estado-ilu")).toBeHidden();
});
