// #516: si el adoptante responde «Ahora no» al seguimiento (30, 90 y 180 días), no ve matches
// sino «Adoptar es para siempre»; al aceptar, aparecen. El servidor se simula con page.route y
// hace lo mismo que el real: sin seguimiento, las recomendaciones responden 403 con su motivo.
import { expect, test } from "@playwright/test";

const LUNA = { animal_id: 1, nombre: "Luna", especie: "perro", descripcion: "Perrita tranquila y cariñosa",
  tamano: "mediano", energia: "media", edad_meses: 24, apto_ninos: true, apto_otros_animales: true,
  necesita_patio: false, foto: null };

async function simular(page) {
  const estado = { perfil: null, recomendacionesSinSeguimiento: 0 };
  await page.route("**/auth/token", (r) => r.fulfill({ json: { access_token: "x", token_type: "bearer" } }));
  await page.route("**/auth/yo", (r) => r.fulfill({ json: { correo: "a@correo.co", nombre: "Ana", rol: "adoptante" } }));
  await page.route("**/adoptantes/yo/perfil", async (r) => {
    if (r.request().method() === "PUT") {
      estado.perfil = r.request().postDataJSON();
      return r.fulfill({ json: estado.perfil });
    }
    return estado.perfil ? r.fulfill({ json: estado.perfil }) : r.fulfill({ status: 404, json: { detail: "Sin perfil" } });
  });
  await page.route("**/adopciones/solicitudes/mias", (r) => r.fulfill({ json: [] }));
  await page.route("**/adopciones/animales", (r) => r.fulfill({ json: [LUNA] }));
  await page.route("**/adopciones/coleccion", (r) => r.fulfill({ json: { esperando: 1, adoptados_total: 0, adoptados: [] } }));
  await page.route("**/adopciones/recomendaciones", (r) => {
    if (!estado.perfil?.acepta_seguimiento) {
      estado.recomendacionesSinSeguimiento += 1;
      return r.fulfill({ status: 403, json: { detail: "RN-10", motivo: "seguimiento_no_aceptado" } });
    }
    return r.fulfill({ json: [{ ...LUNA, puntaje: 90, razones: ["encaja"], alertas: [], restricciones: [] }] });
  });
  await page.goto("/panel/");
  await page.getByLabel("Correo").fill("a@correo.co");
  await page.getByLabel("Contraseña").fill("una-clave-cualquiera");
  await page.getByRole("button", { name: "Entrar" }).click();
  return estado;
}

for (const ancho of [1440, 390]) {
  test(`${ancho} px: con «Ahora no» no hay matches; al aceptar, aparecen`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: 900 });
    const estado = await simular(page);
    await page.getByRole("button", { name: "¡Empezar!" }).click();
    for (let i = 0; i < 8; i++) await page.locator(".opcion").first().click();
    await page.getByRole("button", { name: /Ahora no/ }).click();

    const titulo = page.getByRole("heading", { name: "Ellos nos necesitan también después de llegar a casa 💛" });
    await expect(titulo).toBeVisible();
    await expect(page.getByText("Adoptar es para siempre")).toBeVisible();
    await expect(page.locator(".acompanar-dias li")).toHaveText(["30días", "90días", "180días"]);
    await expect(page.getByRole("heading", { name: "¡Ellos combinan contigo!" })).toHaveCount(0);
    await expect.poll(() => estado.perfil?.acepta_seguimiento).toBe(false); // la respuesta se guardó
    expect(estado.recomendacionesSinSeguimiento).toBe(0); // la app ni las pide

    // «Ver a los peludos sin solicitar»: el catálogo sin el botón de solicitar.
    await page.getByRole("button", { name: "Ver a los peludos sin solicitar" }).click();
    await expect(page.getByRole("button", { name: /Te elijo/ })).toHaveCount(0);

    // Desde «Ver mis compañeros» vuelve la misma pantalla.
    await page.getByRole("button", { name: "Atrás" }).first().click();
    await page.getByRole("button", { name: "Ver mis compañeros con mis respuestas guardadas" }).click();
    await expect(titulo).toBeVisible();

    await page.getByRole("button", { name: "Sí, acepto acompañarlos" }).click();
    await expect(page.getByRole("heading", { name: "¡Ellos combinan contigo!" })).toBeVisible();
    expect(estado.perfil.acepta_seguimiento).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  });
}
