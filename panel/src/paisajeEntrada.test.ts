import { describe, expect, it } from "vitest";

// El CSS lo revisa tests/test_ilustraciones.py (Vitest no lee las hojas de estilo).
const fuentes = import.meta.glob(["./PaisajeEntrada.tsx", "./AccesoAdoptante.tsx"],
  { query: "?raw", import: "default", eager: true }) as Record<string, string>;
const imagenes = Object.keys(import.meta.glob("./img/entrada/*"));

describe("entrada del adoptante: gatitos en el muro y hojas (#482)", () => {
  it("cada imagen en webp con respaldo jpg o png", () => {
    // #484: una sola foto de los gatitos, en su tamaño real (1200 × 675), sin las versiones escaladas.
    expect(imagenes.filter((i) => i.includes("gatos-muro")).sort())
      .toEqual(["./img/entrada/gatos-muro.jpg", "./img/entrada/gatos-muro.webp"]);
    for (const lado of ["izq", "der"]) {
      expect(imagenes).toContain(`./img/entrada/hojas-${lado}.webp`);
      expect(imagenes).toContain(`./img/entrada/hojas-${lado}.png`);
    }
  });

  it("decorativas: ocultas al lector, sin texto alternativo, sin eventos y con carga diferida", () => {
    const vista = fuentes["./PaisajeEntrada.tsx"];
    expect(vista).toContain('aria-hidden="true"');
    const imgs = vista.match(/<img /g)?.length;
    expect(imgs).toBe(2); // las hojas (una por lado, en un map) y la franja
    for (const atributo of [/alt=""/g, /loading="lazy"/g, /type="image\/webp"/g]) expect(vista.match(atributo)).toHaveLength(imgs!);
  });

  it("en la entrada, «Entrar» y «Crear» (#488), no en el catálogo; sin tocar sus textos ni tarjetas", () => {
    const acceso = fuentes["./AccesoAdoptante.tsx"];
    expect(acceso).toContain('const conPaisaje = vista !== "animales";');
    expect(acceso).toContain("{conPaisaje && <PaisajeEntrada />}");
    expect(acceso.match(/<PaisajeEntrada \/>/g)).toHaveLength(1); // un solo lugar: no se vuelve a montar
    expect(acceso).toContain("¡Vamos a encontrar a tu compañero!");
    expect(acceso).toContain('onClick={() => alCambiar("entrar")}');
  });
});
