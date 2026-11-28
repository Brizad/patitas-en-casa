import { describe, expect, it } from "vitest";
import type { AnimalPublicado } from "./apiAdopcion";
import {
  barrasCarta, coleccionNumerada, filtrarColeccion, filtrosColeccion, metaCarta, saludCarta, tipoCarta, trio,
} from "./datosCarta";

const BASE: AnimalPublicado = {
  animal_id: 6, nombre: "Lupe", especie: "perro", descripcion: "", tamano: "mediano", energia: "media",
  edad_meses: 24, apto_ninos: true, apto_otros_animales: true, necesita_patio: false,
};

describe("cartas de Adoptar (#508)", () => {
  it("sin datos no se dibuja ni barra, ni tipo, ni salud", () => {
    expect(barrasCarta(BASE)).toEqual([]);
    expect(tipoCarta(BASE)).toBeNull();
    expect(saludCarta(BASE)).toEqual([]);
    const vacio = { ...BASE, tipo: null, estadisticas: { energia: null, carino: null, juego: null, paciencia: null },
                    salud: { vacunas: null, esterilizado: null, desparasitado: null } };
    expect([barrasCarta(vacio), tipoCarta(vacio), saludCarta(vacio)]).toEqual([[], null, []]);
  });

  it("solo las estadísticas y la salud que tienen dato", () => {
    const a = { ...BASE, tipo: "carinoso" as const,
                estadisticas: { energia: 3, carino: 5, juego: null, paciencia: 5 },
                salud: { vacunas: true, esterilizado: false, desparasitado: null } };
    expect(barrasCarta(a).map((b) => [b.nombre, b.valor])).toEqual(
      [["Energía", 3], ["Cariño", 5], ["Paciencia", 5]]);
    expect(saludCarta(a).map((s) => [s.largo, s.si])).toEqual([["Vacunas al día", true], ["Esterilizado", false]]);
    expect(tipoCarta(a)).toEqual(["Cariñoso", "#E9E2FF"]);
  });

  it("la línea de datos y el mejor match en el centro", () => {
    expect(metaCarta(BASE)).toBe("Perro · Mediano · 2 años");
    expect(metaCarta({ ...BASE, especie: "gato", tamano: "pequeno", edad_meses: 3 })).toBe("Gato · Pequeño · 3 meses");
    expect(trio(["1.º", "2.º", "3.º"])).toEqual(["2.º", "1.º", "3.º"]);
    expect(trio(["1.º"])).toEqual(["1.º"]);
  });
});

describe("La colección (#508)", () => {
  const disponibles = [{ ...BASE, animal_id: 9, nombre: "Max", tipo: "jugueton" as const },
    { ...BASE, animal_id: 2, nombre: "Toby", tipo: "jugueton" as const },
    { ...BASE, animal_id: 5, nombre: "Luna", especie: "gato", tipo: "carinoso" as const }];
  const adoptados = [{ ...BASE, animal_id: 3, nombre: "Bruno" }];
  const items = coleccionNumerada(disponibles, adoptados);

  it("numera por orden de ingreso y marca solo a los adoptados que manda el servidor", () => {
    expect(items.map((x) => [x.numero, x.a.nombre, x.adoptado])).toEqual(
      [["#01", "Toby", false], ["#02", "Bruno", true], ["#03", "Luna", false], ["#04", "Max", false]]);
  });

  it("filtra por tipo y especie, y solo ofrece los tipos que hay", () => {
    expect(filtrosColeccion(items).map(([, n]) => n)).toEqual(["Todos", "Juguetón", "Cariñoso", "Perros", "Gatos"]);
    expect(filtrarColeccion(items, "jugueton").map((x) => x.a.nombre)).toEqual(["Toby", "Max"]);
    expect(filtrarColeccion(items, "gato").map((x) => x.a.nombre)).toEqual(["Luna"]);
    expect(filtrarColeccion(items, "todos")).toHaveLength(4);
  });
});
