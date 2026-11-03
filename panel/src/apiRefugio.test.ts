import { describe, expect, it } from "vitest";
import { ErrorApi } from "./api";
import { Ingreso, MOTIVOS_EGRESO, TIPOS_NOTA, cuerpoIngreso, errorIngreso, nivelOcupacion }
  from "./apiRefugio";

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

const BASE: Ingreso = { nombre: " Luna ", especie: "perro", estado_salud: " sana ", vacunado: true,
                        esterilizado: false };

describe("cuerpoIngreso (código del reporte opcional)", () => {
  it("sin código no envía «reporte»", () => {
    expect(cuerpoIngreso(BASE, "   ")).not.toHaveProperty("reporte");
  });
  it("con código lo envía recortado como «reporte»", () => {
    const c = cuerpoIngreso(BASE, " ab12cd ");
    expect(c.reporte).toBe("ab12cd");
    expect(c.nombre).toBe("Luna");
    expect(c.estado_salud).toBe("sana");
  });
});

describe("errorIngreso", () => {
  it("409 es falta de cupos (RN-04)", () => {
    expect(errorIngreso(new ErrorApi(409, "x"), true)).toMatch(/no tiene cupos/);
  });
  it("422 con código dice que el reporte no existe", () => {
    expect(errorIngreso(new ErrorApi(422, "No existe un reporte con ese código."), true))
      .toMatch(/No existe un reporte con ese código/);
  });
  it("422 sin código no culpa al código", () => {
    expect(errorIngreso(new ErrorApi(422, "Falta el nombre."), false))
      .not.toMatch(/reporte/);
  });
});
