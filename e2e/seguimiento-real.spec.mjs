// #504: el MISMO recorrido de seguimiento-mapa.spec.mjs, pero con un rescate REAL (sin simulación):
// la ubicación sale del navegador (geolocalización falsa de Playwright), el ciudadano lo ve en el
// mapa, a menos de 100 m aparece «Parece que ya llegaste», el rescatista toca «Ya estoy en el
// sitio» y termina con el mismo informe con foto y el mismo resultado.
import { expect, test } from "@playwright/test";
import { ANIMAL, CLAVE, casoEnCamino, entrar, terminarConInforme } from "./rescate-comun.mjs";

test.beforeAll(() => {
  if (!CLAVE) throw new Error("Falta PATITAS_DEMO_CONTRASENA (ver docs/aprende/e2e.md).");
});

test("rescate real: compartir ubicación, llegar, informe con foto y el veterinario la ve", async ({ browser, request }) => {
  test.setTimeout(120_000);
  const codigo = await casoEnCamino(request, "Gato atropellado en la esquina del colegio, sangra de una pata");

  // ~1,2 km al norte del animal.
  const contexto = await browser.newContext({ permissions: ["geolocation"],
    geolocation: { latitude: ANIMAL.latitud + 0.0108, longitude: ANIMAL.longitud } });
  const panel = await contexto.newPage();
  await entrar(panel, "rescatista");
  await expect(panel.getByRole("heading", { name: `Mi rescate ${codigo}` })).toBeVisible();
  await panel.getByLabel(/Autorizo compartir mi ubicación/).check();
  await panel.getByRole("button", { name: "Compartir mi ubicación" }).click();
  await expect(panel.getByText("Mantén la app abierta mientras vas en camino.")).toBeVisible();
  await expect(panel.locator(".aviso-llegaste")).toHaveCount(0); // aún lejos

  const ciudadano = await contexto.newPage();
  await ciudadano.setViewportSize({ width: 390, height: 844 });
  await ciudadano.goto(`/app/#estado/${codigo}`);
  await expect(ciudadano.locator("#estado-mapa")).toBeVisible({ timeout: 20_000 });
  await expect(ciudadano.locator("#mapa-franja")).toHaveText(/^A 1,2 km · llega en unos \d+ min \(aprox\.\)$/);
  await expect(ciudadano.locator("#mapa-demo")).toBeHidden(); // no es una demostración

  // A ~50 m del animal: «Parece que ya llegaste», con el botón resaltado; no cambia de estado solo.
  await contexto.setGeolocation({ latitude: ANIMAL.latitud + 0.00045, longitude: ANIMAL.longitud });
  await expect(panel.getByText("Parece que ya llegaste.")).toBeVisible({ timeout: 15_000 });
  const llegue = panel.getByRole("button", { name: "Ya estoy en el sitio" });
  await expect(llegue).toHaveClass(/resaltado/);
  await expect(panel.locator(".informe-form")).toHaveCount(0);
  await llegue.click();
  await expect(panel.getByRole("status")).toHaveText("Llegada registrada.");

  // Igual que la simulación: el ciudadano ve la llegada con su hora y vuelve la ilustración.
  await ciudadano.locator("#consulta button").click();
  await expect(ciudadano.locator("#estado-mapa")).toBeHidden();
  await expect(ciudadano.locator("#res-pasos li").nth(3)).toContainText("El rescatista llegó al lugar");
  await expect(ciudadano.locator("#res-pasos li").nth(3)).toHaveClass("hecho");

  await terminarConInforme(panel, ciudadano, browser, codigo);
  await contexto.close();
});
