// #490 / #506: «Estado del reporte» con una ilustración, un título y una frase según el estado real que
// devuelve el servidor. Las respuestas se simulan con page.route (las mismas formas que
// GET /reportes/{codigo}/seguimiento).
import { expect, test } from "@playwright/test";

const paso = (nombre, estado, detalle = null) => ({ nombre, estado, detalle, fecha: null });
const NOMBRES = ["Recibido", "Revisado por el veterinario", "Rescatista en camino", "El rescatista llegó al lugar",
  "Atendido", "Cerrado"];
const conActual = (i, detalle = null) => NOMBRES.map((n, j) =>
  paso(n, j < i ? "hecho" : j === i ? "actual" : "pendiente", j === i ? detalle : null));

const ROSA = "rgb(232, 80, 138)", MENTA = "rgb(215, 240, 220)", LILA = "rgb(155, 131, 250)";
// [código, pasos, etapa, foto, título, color del punto]
const CASOS = [
  ["AAAA1111", conActual(1), "recibido", "recibido", "Recibimos tu reporte", "rgb(255, 210, 63)"],
  ["BBBB2222", conActual(2, "Buscando rescatista disponible"), "revisado", "revisado", "Un veterinario lo revisó", LILA],
  ["CCCC3333", conActual(2), "camino", "rescate", "El rescate va en camino", ROSA],
  ["DDDD4444", conActual(4, "El rescatista está con el animal"), "sitio", "rescate", "El rescatista llegó", ROSA],
  ["FFFF6666", conActual(5), "atendido", "rescate", "¡Lo atendimos!", MENTA],
  ["EEEE5555", NOMBRES.map((n) => paso(n, "hecho")), "cerrado", "cerrado", "¡Caso cerrado!", MENTA],
  ["GGGG7777", [paso("Recibido", "hecho"), paso("Cerrado", "hecho", "No pudimos verificar el reporte")],
    "archivado", "espera", "Caso cerrado", LILA],
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
  test(`${ancho} px: la imagen y el mensaje siguen el estado real y vuelven a la espera si el código no existe`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: alto });
    await simular(page);
    await page.goto("/app/#estado");
    const marco = page.locator("#estado-ilu");
    await expect(marco).toHaveAttribute("aria-hidden", "true");
    await expect(marco).toHaveAttribute("data-etapa", "espera");
    await expect(page.locator("#estado-titulo")).toHaveText("Consulta tu reporte");
    await expect(page.locator("#estado-frase")).toHaveText("Tu código está en el mensaje que recibiste al reportar.");
    for (const img of await marco.locator("img").all()) await expect(img).toHaveAttribute("alt", "");
    // #506: antes de consultar, los 6 pasos (3 columnas en computador, 2 en el celular).
    const vacia = page.locator("#estado-vacia");
    await expect(vacia.getByRole("heading", { name: "Así vas a seguir tu reporte" })).toBeVisible();
    await expect(vacia.locator(".ruta li")).toHaveCount(6);
    const columnas = await vacia.locator(".ruta").evaluate((r) => getComputedStyle(r).gridTemplateColumns.split(" ").length);
    expect(columnas).toBe(ancho >= 1024 ? 3 : 2);
    await expect(vacia.getByRole("link", { name: "Hacer un reporte" })).toHaveAttribute("href", "#reportar");

    for (const [codigo, pasos, etapa, foto, titulo, color] of CASOS) {
      await consultar(page, codigo);
      await expect(marco).toHaveAttribute("data-etapa", etapa);
      await expect(page.locator("#estado-titulo")).toHaveText(titulo);
      await expect.poll(() => visible(page).evaluate((i) => i.complete && i.currentSrc)).toMatch(`-${foto}.webp`);
      await expect(page.locator("#estado-texto")).not.toHaveClass(/fuera/);
      expect(await page.locator(".estado-punto").evaluate((p) => getComputedStyle(p).backgroundColor)).toBe(color);
      await expect(page.locator("#res-pasos li")).toHaveCount(pasos.length); // la línea de tiempo, igual que antes
      await expect(vacia).toBeHidden();
    }
    await consultar(page, "ZZZZ9999");
    await expect(page.locator("#mensaje")).toContainText("No encontramos el código ZZZZ9999");
    await expect(marco).toHaveAttribute("data-etapa", "espera");
    await expect(vacia).toBeVisible();

    // #494 / #506: sin marco; la foto completa con su proporción real y los 4 bordes desvanecidos en el crema.
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
    const texto = await page.locator("#estado-texto").boundingBox();
    expect(Math.round(f.height)).toBe(ancho >= 1024 ? 600 : 280);
    expect(texto.y).toBeLessThan(f.y + f.height); // montado sobre el desvanecido de abajo
    expect(Math.abs(texto.x + texto.width / 2 - (f.x + f.width / 2))).toBeLessThan(2); // centrado
    if (ancho >= 1024) { // 5fr | 6fr, máx. 1200 px; foto centrada en su columna y todo en el centro de la pantalla
      const campo = await page.locator("#codigo").boundingBox();
      const estado = await page.locator("#pantalla-estado").boundingBox();
      const columna = await marco.boundingBox();
      expect(Math.round(estado.width)).toBe(1200);
      expect(Math.abs(columna.width - (1200 - 24) * 6 / 11)).toBeLessThan(1);
      expect(f.x).toBeGreaterThan(campo.x + campo.width);
      expect(Math.abs(f.x + f.width / 2 - (columna.x + columna.width / 2))).toBeLessThan(2);
      expect(Math.abs(columna.y + columna.height / 2 - (estado.y + estado.height / 2))).toBeLessThan(2);
      expect(estado.y + estado.height).toBeLessThanOrEqual(alto); // cabe en la pantalla
    } else { // celular: arriba de todo, centrada
      const titulo = await page.getByRole("heading", { name: "Estado del reporte" }).boundingBox();
      expect(texto.y + texto.height).toBeLessThanOrEqual(titulo.y);
      expect(Math.abs(f.x + f.width / 2 - ancho / 2)).toBeLessThan(2);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  });
}

test("con «reducir movimiento» la imagen cambia sin fundido", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await simular(page);
  await page.goto("/app/#estado");
  for (const elemento of ["#estado-ilu img", "#estado-texto"]) { // foto y texto, sin fundido
    const transicion = await page.locator(elemento).evaluate((e) => getComputedStyle(e).transitionDuration);
    expect(transicion).toBe("0s");
  }
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
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app/#estado/EEEE5555");
  await expect(page.locator("#mapa-franja")).toHaveText("A 1,2 km · llega en unos 3 min (aprox.)");
  await expect(page.locator("#estado-ilu")).toBeHidden();
  // #502: la franja no tapa el nombre del rescatista (en el celular, el rescatista va arriba).
  await expect(page.locator(".nombre-rescatista")).toHaveText("Rita");
  await page.waitForTimeout(1500); // el encuadre se anima
  const nombre = await page.locator(".nombre-rescatista").boundingBox();
  const franja = await page.locator("#mapa-franja").boundingBox();
  expect(nombre.y).toBeGreaterThanOrEqual(franja.y + franja.height);
});
