// #496: bandejas del personal con el orden único (nivel y luego el más antiguo) y la consulta del
// ciudadano con su posición en la cola. Archivar y los atrasados (más de 72 h) los cubre pytest:
// aquí no se puede envejecer un reporte.
import { expect, test } from "@playwright/test";

const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const NIVELES = ["Urgente", "Alta", "Normal"];

test.beforeAll(() => {
  if (!CLAVE) throw new Error("Falta PATITAS_DEMO_CONTRASENA (ver docs/aprende/e2e.md).");
});

async function entrar(page, usuario) {
  await page.goto("about:blank");
  await page.goto("/panel/");
  await page.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await page.getByLabel("Contraseña").fill(CLAVE);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("button", { name: "Salir" })).toBeVisible();
}

for (const [ancho, alto] of [[1440, 900], [390, 844]]) {
  test(`${ancho} px: la cola va por nivel, con resumen, pestañas y espera`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: alto });
    await entrar(page, "veterinaria");
    await expect(page.locator(".resumen-cola")).toHaveText(/^Por revisar: \d+ · Urgentes: \d+ · Atrasados: \d+$/);
    for (const nombre of [/Por revisar/, /Atrasados/, /Revisados hoy/]) {
      await expect(page.getByRole("tab", { name: nombre })).toBeVisible();
    }
    const niveles = await page.locator(".tarjeta-caso .nivel").allInnerTexts();
    expect(niveles.length).toBeGreaterThan(0);
    const rangos = niveles.map((n) => NIVELES.indexOf(n));
    expect(rangos).toEqual([...rangos].sort((a, b) => a - b)); // Urgente > Alta > Normal
    const espera = page.locator(".tarjeta-caso .espera").first();
    await expect(espera).toHaveText(/^hace /);
    await expect(espera).toHaveAttribute("title", /\d{4}/); // fecha exacta al pasar el mouse
    await page.getByRole("tab", { name: /Revisados hoy/ }).click();
    await expect(page.locator(".pestanas-bandeja [aria-selected='true']")).toHaveText("Revisados hoy");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  });

  test(`${ancho} px: el rescatista ve tiempo y «—» de distancia sin ubicación`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: alto });
    await entrar(page, "rescatista");
    await page.getByRole("button", { name: "Ahora no" }).click(); // no comparte su ubicación
    const oferta = page.locator("li.oferta").first();
    await expect(oferta).toBeVisible();
    await expect(oferta.locator(".distancia")).toHaveText("Distancia: —");
    await expect(oferta).toContainText(/Reportado hace /);
    await expect(oferta.getByRole("button", { name: "Aceptar rescate" })).toBeVisible();
    await oferta.getByRole("button", { name: "Ver detalle" }).click();
    await expect(oferta.locator(".oferta-detalle")).toBeVisible();
    if (ancho >= 1100) {
      await expect(page.locator(".mapa-casos")).toBeVisible();
    } else {
      await expect(page.locator(".mapa-casos")).toBeHidden();
      await page.getByRole("button", { name: "Ver en mapa" }).click();
      await expect(page.locator(".mapa-casos")).toBeVisible();
    }
    for (const nombre of [/Disponibles/, /Mis rescates/, /Atrasados/]) {
      await expect(page.getByRole("tab", { name: nombre })).toBeVisible();
    }
  });
}

test("el ciudadano ve su lugar en la cola y la hora de cada paso", async ({ page, request }) => {
  const r = await request.post("/reportes", { data: {
    descripcion: "Gato con una pata lastimada en el parque, cojea pero come bien",
    direccion: "Parque Santander, Cúcuta" } });
  const { codigo } = await r.json();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/app/#estado/${codigo}`);
  await expect(page.locator("#res-cola")).toHaveText(
    /^(Eres el siguiente en la cola\.|Tu reporte está en la cola del veterinario\. Hay \d+ casos? antes que el tuyo\.)$/);
  await expect(page.locator("#res-nivel")).toBeHidden(); // la prioridad, solo después del triaje
  await expect(page.locator("#res-pasos li.hecho .detalle").first()).toHaveText(/\d{1,2}:\d{2}/);
});
