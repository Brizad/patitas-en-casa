import { describe, expect, it } from "vitest";
import { NOMBRE_ACCION, fechaLocal } from "./apiHistorial";

describe("historial del veterinario", () => {
  it("la fecha UTC se muestra en la hora local", () => {
    expect(fechaLocal("2026-10-03T14:00:00+00:00", "America/Bogota")).toContain("09:00");
    expect(fechaLocal("2026-10-03T03:00:00+00:00", "America/Bogota")).toContain("02/10/2026");
  });
  it("cada acción tiene un nombre legible", () => {
    expect(Object.values(NOMBRE_ACCION)).toEqual(["Confirmado", "Ajustado", "Descartado"]);
  });
});
