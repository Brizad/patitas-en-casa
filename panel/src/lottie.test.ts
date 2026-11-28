import { describe, expect, it } from "vitest";
import { decidir } from "./Lottie";

const fuentes = import.meta.glob("./*.tsx", { query: "?raw", import: "default", eager: true });

describe("animaciones Lottie (decorativas)", () => {
  it("con movimiento, anima; con movimiento reducido, el dibujo de siempre o un cuadro quieto", () => {
    expect(decidir(false, "respaldo")).toBe("animar");
    expect(decidir(false, "cuadro")).toBe("animar");
    expect(decidir(true, "respaldo")).toBe("respaldo");
    expect(decidir(true, "cuadro")).toBe("cuadro");
  });

  it("se cargan tarde (al verse), son aria-hidden y salen del propio sitio", () => {
    const lottie = fuentes["./Lottie.tsx"] as string;
    expect(lottie).toContain("new IntersectionObserver");
    expect(lottie).toContain('import("lottie-web/build/player/lottie_light")');  // sin eval: CSP igual
    expect(lottie).toContain("fetch(`/diseno/lottie/");
    expect(lottie).toContain('aria-hidden="true"');
    expect(lottie).toContain('el.closest(".adop--quieto")');
  });

  it("cada animación en su sitio; #508: «Adoptar» ya no tiene animalitos caminando", () => {
    expect(fuentes["./Animalitos.tsx"]).toBeUndefined();
    expect(fuentes["./AdoptantePantallas.tsx"]).not.toContain("Animalitos");
    expect(fuentes["./Cargando.tsx"]).toContain('nombre="huellas-cargando"');
    expect(fuentes["./AdoptantePantallas.tsx"]).toContain('nombre="perrito-saltando"');
    expect(fuentes["./AdoptantePantallas.tsx"]).toContain('nombre="gatos-jugando"');
  });
});
