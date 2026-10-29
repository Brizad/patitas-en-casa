import { describe, expect, it } from "vitest";
import { PERFIL_VACIO, resumenAnimal } from "./apiAdopcion";
import { resumenPerfil } from "./apiAdopcionCoordinador";

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

describe("resumenPerfil", () => {
  it("resume el perfil para decidir sin otra pantalla", () => {
    expect(resumenPerfil(null)).toBe("Sin perfil");
    expect(resumenPerfil({ ...PERFIL_VACIO, hay_ninos: true })).toBe(
      "casa · sin patio · hay niños · sin otros animales · 4 h solo al día · sin experiencia");
  });
});
