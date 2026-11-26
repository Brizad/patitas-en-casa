// Regresión visual (#316): compara cada pantalla con su captura base (e2e/capturas/), para que un
// cambio de estilo no pase sin que nadie lo vea. Página de inicio, PWA y una pantalla por rol del
// panel, a 360 y 1440 px, en claro.
//
// - Corre primero (orden alfabético): solo están los datos de demostración, aún sin los reportes
//   que crean flujo.spec.mjs y piloto.spec.mjs.
// - Lo que cambia en cada arranque (códigos aleatorios, «hace N min», tiempos medidos) se tapa
//   con una máscara; el resto debe coincidir con una tolerancia baja (playwright.config.mjs).
// - Las capturas base se toman en Linux (el CI): en Windows las fuentes se dibujan distinto, así
//   que aquí se omiten. Cómo actualizarlas a propósito: docs/aprende/e2e.md.
import { expect, test } from "@playwright/test";

const CLAVE = process.env.PATITAS_DEMO_CONTRASENA;
const ANCHOS = [360, 1440];

test.skip(process.platform !== "linux", "Las capturas base son de Linux (CI); ver docs/aprende/e2e.md");

async function comparar(page, nombre, mascaras = []) {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  await expect(page).toHaveScreenshot(`${nombre}.png`, {
    fullPage: true, animations: "disabled", caret: "hide",
    mask: mascaras.map((selector) => page.locator(selector)),
  });
}

async function entrar(page, usuario) {
  await page.goto("/panel/");
  await page.getByLabel("Correo").fill(`${usuario}@demo.patitas.co`);
  await page.getByLabel("Contraseña").fill(CLAVE);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("button", { name: "Salir" })).toBeVisible();
}

// Pantalla de inicio de cada rol y lo que en ella cambia entre corridas.
const ROLES = [
  ["veterinaria", "veterinario-cola", ["code", ".item > .ds-suave"]],
  ["coordinador", "coordinador-refugio", []],
  ["rescatista", "rescatista-ofertas", ["code"]],
  ["adoptante", "adoptante-catalogo", []],
  ["admin", "administrador-cuentas", []],
  ["alcaldia", "alcaldia-indicadores", [".kpi dd", "h3 + .lista-simple"]],
];

for (const ancho of ANCHOS) {
  test.describe(`${ancho} px`, () => {
    // #470: con «reducir movimiento», las animaciones Lottie muestran su dibujo de siempre o un
    // cuadro quieto; si no, cada captura las toma en un cuadro distinto y la comparación falla al azar.
    test.use({ viewport: { width: ancho, height: 900 }, colorScheme: "light", reducedMotion: "reduce" });

    test("página de inicio", async ({ page }) => {
      await page.goto("/");
      await comparar(page, `inicio-${ancho}`);
    });

    test("PWA: reportar emergencia", async ({ page }) => {
      await page.goto("/app/#reportar");
      await comparar(page, `pwa-reportar-${ancho}`);
    });

    for (const [usuario, nombre, mascaras] of ROLES) {
      test(`panel: ${nombre}`, async ({ page }) => {
        test.skip(!CLAVE, "Falta PATITAS_DEMO_CONTRASENA (ver docs/aprende/e2e.md).");
        await entrar(page, usuario);
        await comparar(page, `${nombre}-${ancho}`, mascaras);
      });
    }
  });
}
