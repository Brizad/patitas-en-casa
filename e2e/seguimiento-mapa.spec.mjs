// #498 / #504: «Simular recorrido» de principio a fin, en un solo navegador con dos pestañas: el
// panel del rescatista de demostración y la consulta del ciudadano. El servidor mueve la posición
// 1,5 km hasta el animal en ~90 s; la consulta lo ve acercarse y decir «¡Está llegando!». Al llegar
// queda «En el sitio» (no «Atendido»): desde ahí el informe con foto es el MISMO del rescate real
// (rescate-comun.mjs, igual que seguimiento-real.spec.mjs).
import { expect, test } from "@playwright/test";
import { CLAVE, casoEnCamino, entrar, terminarConInforme } from "./rescate-comun.mjs";

test.beforeAll(() => {
  if (!CLAVE) throw new Error("Falta PATITAS_DEMO_CONTRASENA (ver docs/aprende/e2e.md).");
});

test("recorrido de demostración: acercarse, llegar, informe con foto y el veterinario la ve", async ({ browser, request }) => {
  test.setTimeout(240_000);
  const codigo = await casoEnCamino(request, "Perro atropellado frente al parque, sangra y no se puede levantar");

  const contexto = await browser.newContext();
  const panel = await contexto.newPage();
  await entrar(panel, "rescatista");
  await expect(panel.getByRole("heading", { name: `Mi rescate ${codigo}` })).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Compartir mi ubicación mientras voy en camino" })).toBeVisible();
  await panel.getByRole("button", { name: "Simular recorrido" }).click();
  await expect(panel.getByRole("status")).toContainText("Recorrido de demostración en marcha");

  const ciudadano = await contexto.newPage();
  await ciudadano.setViewportSize({ width: 390, height: 844 });
  await ciudadano.goto(`/app/#estado/${codigo}`);
  const mapa = ciudadano.locator("#estado-mapa");
  await expect(mapa).toBeVisible({ timeout: 20_000 });
  await expect(ciudadano.locator("#estado-ilu")).toBeHidden();
  await expect(ciudadano.locator("#mapa-demo")).toHaveText("Recorrido de demostración");
  const franja = ciudadano.locator("#mapa-franja");
  await expect(franja).toHaveText(/^A [\d,]+ (km|m) · llega en unos \d+ min \(aprox\.\)$/, { timeout: 30_000 });
  await expect(ciudadano.locator(".nombre-rescatista")).toHaveText("Rita"); // solo el nombre de pila
  await expect(franja).toHaveText("¡Está llegando!", { timeout: 110_000 });

  // #504: al llegar queda «En el sitio» (no «Atendido»): el mapa se va y vuelve la ilustración.
  await expect(mapa).toBeHidden({ timeout: 40_000 });
  await expect(ciudadano.locator("#estado-ilu")).toBeVisible();
  const pasos = ciudadano.locator("#res-pasos li");
  await expect(pasos.nth(3)).toContainText("El rescatista llegó al lugar");
  await expect(pasos.nth(3)).toHaveClass("hecho");
  await expect(pasos.nth(4)).toHaveClass("actual");

  await terminarConInforme(panel, ciudadano, browser, codigo);
  await contexto.close();
});

test("sin sesión, el servidor rechaza la simulación (401; sin cuenta de demostración, 403 en pytest)", async ({ request }) => {
  const r = await request.post("/rescates/AAAA1111/simulacion");
  expect(r.status()).toBe(401); // sin sesión
});
