import { describe, expect, it } from "vitest";
import type { AnimalPublicado } from "./apiAdopcion";
import { convivenciaIconos, finDeFila } from "./flujoAdopcion";

const pantallas = import.meta.glob("./*.tsx", { query: "?raw", import: "default", eager: true });

describe("«Esperan un hogar»: detalle debajo de la fila (#477)", () => {
  it("el panel va después de la última tarjeta de la fila tocada", () => {
    expect([0, 1, 2].map((i) => finDeFila(i, 2, 3))).toEqual([1, 1, 2]); // celular: la fila 2 está incompleta
    expect([finDeFila(4, 6, 9), finDeFila(7, 6, 9), finDeFila(3, 0, 5)]).toEqual([5, 8, 3]);
  });

  it("la convivencia en tres íconos con su texto para el lector de pantalla", () => {
    const a = { apto_ninos: true, apto_otros_animales: false, necesita_patio: true } as AnimalPublicado;
    expect(convivenciaIconos(a)).toEqual([
      { clave: "ninos", marca: "si", texto: "Convive con niños" },
      { clave: "animales", marca: "no", texto: "Mejor sin otros animales" },
      { clave: "patio", marca: "ojo", texto: "Necesita patio" },
    ]);
    expect(convivenciaIconos({ ...a, necesita_patio: false })[2].marca).toBe("si");
  });

  it("tarjetas que son botones con aria-expanded y aria-controls; Esc y la X cierran", () => {
    const vista = pantallas["./CatalogoEnFilas.tsx"] as string;
    expect(vista).toContain("aria-expanded={abierto === a.animal_id}");
    expect(vista).toContain('aria-controls="detalle-animal"');
    for (const texto of ['e.key === "Escape"', 'aria-label="Cerrar"', "sonidoDeEspecie(", "¡Te elijo, ${animal.nombre}!"]) {
      expect(vista).toContain(texto);
    }
    const acceso = pantallas["./AccesoAdoptante.tsx"] as string;
    expect(acceso).toContain("<CatalogoEnFilas");
    expect(acceso).not.toContain("acceso-convive");  // la tarjeta ya no trae texto largo
  });
});
