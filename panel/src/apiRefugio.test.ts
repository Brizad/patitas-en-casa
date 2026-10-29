import { describe, expect, it } from "vitest";
import { nivelOcupacion } from "./apiRefugio";

describe("nivelOcupacion (RN-04)", () => {
  it("alerta desde el 90 % y lleno al 100 %", () => {
    expect(nivelOcupacion(89.9)).toBe("normal");
    expect(nivelOcupacion(90)).toBe("alerta");
    expect(nivelOcupacion(100)).toBe("lleno");
  });
});
