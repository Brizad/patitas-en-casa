import { describe, expect, it } from "vitest";
import { MOTIVOS_EGRESO, TIPOS_NOTA, nivelOcupacion } from "./apiRefugio";

describe("nivelOcupacion (RN-04)", () => {
  it("alerta desde el 90 % y lleno al 100 %", () => {
    expect(nivelOcupacion(89.9)).toBe("normal");
    expect(nivelOcupacion(90)).toBe("alerta");
    expect(nivelOcupacion(100)).toBe("lleno");
  });
});

describe("textos de fichas y egresos", () => {
  it("coinciden con los valores que acepta la API", () => {
    expect(Object.keys(TIPOS_NOTA)).toEqual(
      ["observacion", "tratamiento", "vacuna", "procedimiento"]);
    expect(Object.keys(MOTIVOS_EGRESO)).toEqual(
      ["adopcion", "traslado", "fallecimiento", "devuelto"]);
  });
});
