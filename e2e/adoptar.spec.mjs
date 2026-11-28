// #508: «Adoptar» renovado. Las respuestas del servidor se simulan con page.route (mismas formas
// que la API): así se prueba qué se dibuja con y sin encuesta y que sin datos no sale nada.
import { expect, test } from "@playwright/test";

const SIN = { energia: null, carino: null, juego: null, paciencia: null };
const animal = (id, nombre, extra = {}) => ({
  animal_id: id, nombre, especie: "perro", descripcion: "Una descripción de prueba suficiente", tamano: "mediano",
  energia: "media", edad_meses: 24, apto_ninos: true, apto_otros_animales: true, necesita_patio: false, foto: null,
  estadisticas: SIN, tipo: null, habilidades: [], salud: { vacunas: null, esterilizado: null, desparasitado: null },
  ...extra });
const CATALOGO = [
  animal(1, "Toby", { estadisticas: { energia: 5, carino: 4, juego: 5, paciencia: 2 }, tipo: "jugueton",
    habilidades: ["Rey del juego"], salud: { vacunas: true, esterilizado: false, desparasitado: null } }),
  animal(2, "Lupe", { estadisticas: { energia: 3, carino: 5, juego: 3, paciencia: 5 }, tipo: "carinoso" }),
  animal(3, "Nube"), // sin estadísticas, tipo, habilidades ni salud
  animal(4, "Rocky"),
];

async function entrar(page, { conEncuesta }) {
  await page.route("**/auth/token", (r) => r.fulfill({ json: { access_token: "x", token_type: "bearer" } }));
  await page.route("**/auth/yo", (r) => r.fulfill({ json: { correo: "a@correo.co", nombre: "Ana", rol: "adoptante" } }));
  await page.route("**/adoptantes/yo/perfil", (r) => (conEncuesta
    ? r.fulfill({ json: { vivienda: "casa", tiene_patio: true, hay_ninos: false, otros_animales: false,
      horas_solo_al_dia: 4, experiencia: true, acepta_seguimiento: true } })
    : r.fulfill({ status: 404, json: { detail: "Sin perfil" } })));
  await page.route("**/adopciones/solicitudes/mias", (r) => r.fulfill({ json: [] }));
  await page.route("**/adopciones/animales", (r) => r.fulfill({ json: CATALOGO }));
  await page.route("**/adopciones/recomendaciones", (r) => r.fulfill({
    json: CATALOGO.map((a, i) => ({ ...a, puntaje: 90 - i, razones: ["encaja"], alertas: [], restricciones: [] })) }));
  await page.route("**/adopciones/coleccion", (r) => r.fulfill({ json: { esperando: 4, adoptados_total: 9,
    adoptados: [animal(7, "Bruno", { tipo: "tranquilo", adoptado_en: "2026-11-20T15:00:00Z" })] } }));
  await page.goto("/panel/");
  await page.getByLabel("Correo").fill("a@correo.co");
  await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
  await page.getByRole("button", { name: "Entrar" }).click();
}

for (const ancho of [1440, 390]) {
  test.describe(`${ancho} px`, () => {
    test.use({ viewport: { width: ancho, height: 900 } });

    test("sin encuesta: 3 cartas boca abajo y el botón a la encuesta; sin animalitos caminando", async ({ page }) => {
      await entrar(page, { conEncuesta: false });
      const elige = page.locator(".seccion--elige");
      await expect(elige.getByRole("heading", { name: "¡Elige a tu compañero!" })).toBeVisible();
      await expect(elige.locator(".carta--boca-abajo")).toHaveCount(3);
      await expect(elige.locator("article")).toHaveCount(0); // ningún animal destapado
      await expect(page.locator(".carril, .paseante")).toHaveCount(0);
      await elige.getByRole("button", { name: "Responde la encuesta y descúbrelos" }).click();
      await expect(page.locator(".adop-contador")).toHaveText("1 de 9");
    });

    test("con encuesta: los 3 mejores matches, el primero en el centro y sin datos no se dibuja nada", async ({ page }) => {
      await entrar(page, { conEncuesta: true });
      const cartas = page.locator(".seccion--elige article");
      await expect(cartas).toHaveCount(3);
      await expect(cartas.nth(1).locator(".carta-corona")).toHaveText("★ Tu mejor match"); // en el centro
      const toby = page.locator(".seccion--elige").getByRole("article", { name: "Toby" });
      await expect(toby).toHaveClass(/carta--estrella/);
      await expect(toby.locator(".carta-tipo")).toHaveText("Juguetón");
      await expect(toby.locator(".carta-barras li")).toHaveCount(4);
      await expect(toby.locator(".carta-habilidades li")).toHaveText(["★ Rey del juego"]);
      await expect(toby.locator(".carta-salud li")).toHaveCount(2); // desparasitado: sin dato
      await expect(toby.locator(".carta-salud li.no")).toHaveCount(1);
      await expect(toby.getByRole("img", { name: "Foto de Toby" })).toBeVisible();
      const nube = page.locator(".seccion--elige").getByRole("article", { name: "Nube" });
      await expect(nube.locator(".carta-tipo, .carta-barras, .carta-habilidades, .carta-salud")).toHaveCount(0);
      await expect(nube.getByRole("button", { name: "Elegir a Nube" })).toBeVisible();
      const [a, b, c] = await Promise.all([0, 1, 2].map((i) => cartas.nth(i).boundingBox()));
      if (ancho >= 1024) { // en fila, el mejor en el centro
        expect(a.x).toBeLessThan(b.x);
        expect(b.x).toBeLessThan(c.x);
      } else { // en columna, el mejor arriba
        expect(b.y).toBeLessThan(a.y);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    });

    test("la colección: contador del servidor, numerada, filtros y adoptados en gris sin botón", async ({ page }) => {
      await entrar(page, { conEncuesta: false });
      const col = page.locator("section", { has: page.getByRole("heading", { name: "Conoce a los 4 peludos" }) });
      await expect(col.locator(".coleccion-contador")).toHaveText("Ya encontraron hogar: 9 · Esperando: 4");
      await expect(col.locator(".album > li")).toHaveCount(5);
      await expect(col.locator(".carta-num")).toHaveText(["#01", "#02", "#03", "#04", "#05"]);
      const bruno = col.getByRole("article", { name: "Bruno" });
      await expect(bruno.locator(".carta-sello")).toHaveText("¡Encontró hogar!");
      await expect(bruno.getByRole("button")).toHaveCount(0);
      await expect(bruno).toHaveClass(/carta--adoptada/); // en escala de grises (adoptar-secciones.css)
      await expect(col.getByRole("article", { name: "Toby" }).getByRole("button", { name: "Conocer a Toby" })).toBeVisible();
      await col.getByRole("button", { name: "Cariñoso" }).click();
      await expect(col.locator(".album > li")).toHaveCount(1);
      await expect(col.getByRole("button", { name: "Guardián" })).toHaveCount(0); // solo los tipos que hay
      await expect(page.getByRole("heading", { name: "Cuidados por nuestro equipo veterinario" })).toBeVisible();
      await expect(page.locator(".pasos-adopcion > li")).toHaveCount(5);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    });
  });
}
