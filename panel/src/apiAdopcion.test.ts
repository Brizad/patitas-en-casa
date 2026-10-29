import { describe, expect, it } from "vitest";
import { resumenAnimal } from "./apiAdopcion";

const base = { animal_id: 1, nombre: "Canela", especie: "gato", descripcion: "x",
               tamano: "pequeno", energia: "baja", apto_ninos: true,
               apto_otros_animales: false, necesita_patio: false };

describe("resumenAnimal", () => {
  it("dice la edad en meses o años y lo que necesita", () => {
    expect(resumenAnimal({ ...base, edad_meses: 8 })).toMatch(/^gato, 8 meses/);
    expect(resumenAnimal({ ...base, edad_meses: 12 })).toMatch(/1 año,/);
    expect(resumenAnimal({ ...base, edad_meses: 30 })).toMatch(/2 años/);
    expect(resumenAnimal({ ...base, edad_meses: 30 })).toMatch(/convive con niños, mejor solo$/);
  });
});
