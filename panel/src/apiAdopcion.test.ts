import { describe, expect, it } from "vitest";
import { PERFIL_VACIO, resumenAnimal } from "./apiAdopcion";
import { conEtiqueta, desdeCatalogo, paraEnviar, resumenPerfil } from "./apiAdopcionCoordinador";

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

describe("ficha del coordinador (#422)", () => {
  const publicado = { animal_id: 1, nombre: "Toby", especie: "perro", descripcion: "Aprende rápido",
    tamano: "grande", energia: "alta", edad_meses: 3, apto_ninos: true, apto_otros_animales: true,
    necesita_patio: true, carino: 95, etiquetas: ["Juguetón"], peso_kg: 8 };
  it("lo publicado se carga en el formulario; lo que falta queda vacío", () => {
    const p = desdeCatalogo(publicado);
    expect(p).toMatchObject({ carino: 95, juego: null, etiquetas: ["Juguetón"], peso_kg: 8,
                              peso_adulto_kg: null, tamano: "grande" });
  });
  it("al enviar se quitan espacios y etiquetas vacías (máximo 3)", () => {
    const p = paraEnviar({ ...desdeCatalogo(publicado), descripcion: "  Hola mundo  ",
      etiquetas: [" Leal ", "", "  ", "Guardián", "Otra"] });
    expect(p.descripcion).toBe("Hola mundo");
    expect(p.etiquetas).toEqual(["Leal", "Guardián", "Otra"]);
  });
  it("cambiar la tercera etiqueta no borra las otras", () => {
    expect(conEtiqueta([], 2, "Vacunado")).toEqual(["", "", "Vacunado"]);
    expect(conEtiqueta(["A", "B"], 0, "C")).toEqual(["C", "B"]);
  });
});
