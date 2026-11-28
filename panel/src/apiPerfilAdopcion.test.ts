import { describe, expect, it } from "vitest";
import { ESTADISTICAS, SALUD, TIPOS, aEstadistica, aSalud, deSalud } from "./apiPerfilAdopcion";

describe("perfil de adopción (#508)", () => {
  it("la salud tiene tres estados: sí, no y sin dato (nunca un valor por defecto)", () => {
    expect([true, false, null].map(deSalud)).toEqual(["si", "no", ""]);
    expect(["si", "no", ""].map(aSalud)).toEqual([true, false, null]);
  });

  it("una estadística vacía es «sin dato», no cero", () => {
    expect(aEstadistica("")).toBeNull();
    expect(aEstadistica("4")).toBe(4);
  });

  it("las claves coinciden con las de la API y los 5 tipos tienen nombre", () => {
    expect(ESTADISTICAS.map(([k]) => k)).toEqual(["energia", "carino", "juego", "paciencia"]);
    expect(SALUD.map(([k]) => k)).toEqual(["vacunas", "esterilizado", "desparasitado"]);
    expect(Object.values(TIPOS).map(([nombre]) => nombre)).toEqual(
      ["Juguetón", "Aventurero", "Tranquilo", "Cariñoso", "Guardián"]);
  });
});
