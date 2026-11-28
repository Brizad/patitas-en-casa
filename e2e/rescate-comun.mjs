// #504: pasos compartidos por las e2e del rescate SIMULADO y del REAL. Desde «En el sitio» los dos
// recorren exactamente lo mismo (informe con foto, «Atendido», lo que ven el veterinario y el
// ciudadano), porque el sistema usa el mismo código para ambos.
import { fileURLToPath } from "node:url";
import { expect } from "@playwright/test";

export const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
export const ANIMAL = { latitud: 7.8939, longitud: -72.5078 };
export const FOTO = fileURLToPath(new URL("../app/pwa/fotos/consultar-2-revisado.jpg", import.meta.url));

export async function token(request, usuario) {
  const r = await request.post("/auth/token", {
    form: { username: `${usuario}@demo.patitas.co`, password: CLAVE } });
  expect(r.status()).toBe(200);
  return { Authorization: `Bearer ${(await r.json()).access_token}` };
}

/** Reporte con GPS, confirmado crítico y aceptado por el rescatista de demostración. */
export async function casoEnCamino(request, descripcion) {
  const { codigo } = await (await request.post("/reportes", { data: { descripcion, ...ANIMAL } })).json();
  const vet = await token(request, "veterinaria");
  expect((await request.post(`/reportes/${codigo}/confirmacion`, { headers: vet,
    data: { prioridad: "critica", justificacion: "Sangra y no se puede levantar" } })).status()).toBe(200);
  const resc = await token(request, "rescatista");
  await request.put("/rescatistas/yo/disponibilidad", { headers: resc, data: { disponible: true } });
  expect((await request.post(`/rescates/${codigo}/aceptar`, { headers: resc })).status()).toBe(200);
  return codigo;
}

export async function entrar(page, usuario) {
  await page.goto("/panel/");
  await page.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await page.getByLabel("Contraseña").fill(CLAVE);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("button", { name: "Salir" })).toBeVisible();
}

/** «En el sitio» → informe con una foto → «Atendido»; el ciudadano ve solo el resultado amable
 *  y el veterinario ve el informe con la foto. */
export async function terminarConInforme(panel, ciudadano, browser, codigo) {
  const informe = panel.locator(".informe-form");
  await expect(informe).toBeVisible({ timeout: 30_000 });
  await informe.getByLabel("Herido").check();
  await informe.getByLabel("Trasladado al refugio").check();
  await informe.locator("input[type=file]").setInputFiles(FOTO);
  await expect(informe.locator(".fotos-informe img")).toHaveCount(1);
  await informe.getByLabel(/Nota/).fill("Lo encontré debajo de un carro, se dejó cargar.");
  await informe.getByRole("button", { name: "Enviar informe" }).click();
  await expect(panel.getByRole("status")).toContainText("Informe enviado: lo trasladamos al refugio");

  // El ciudadano: «Atendido» con el resultado amable; nunca la nota ni las fotos.
  await ciudadano.locator("#consulta button").click();
  await expect(ciudadano.locator("#res-pasos li").nth(4)).toContainText("Atendido · Lo trasladamos al refugio");
  await expect(ciudadano.locator("body")).not.toContainText("debajo de un carro");
  await expect(ciudadano.locator("#estado-mapa")).toBeHidden();

  // El veterinario ve el informe con la foto (pedida con su sesión).
  const vet = await browser.newPage();
  await entrar(vet, "veterinaria");
  await vet.getByRole("button", { name: "Informes de rescate" }).click();
  const tarjeta = vet.locator(".informe-rescate", { hasText: codigo });
  await expect(tarjeta).toContainText("Trasladado al refugio");
  await expect(tarjeta).toContainText("Herido");
  await expect(tarjeta).toContainText("debajo de un carro");
  const foto = tarjeta.locator(".galeria img");
  await expect(foto).toHaveCount(1);
  await expect.poll(() => foto.evaluate((i) => i.complete && i.naturalWidth)).toBeGreaterThan(0);
  await tarjeta.getByRole("button", { name: /Ampliar la foto 1/ }).click();
  await expect(vet.getByRole("dialog", { name: "Foto ampliada" })).toBeVisible();
  await vet.keyboard.press("Escape");
  await expect(vet.getByRole("dialog", { name: "Foto ampliada" })).toHaveCount(0);
  await vet.close();
}
