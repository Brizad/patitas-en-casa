import { describe, expect, it } from "vitest";
import { ErrorApi } from "./api";
import { textoError } from "./mensajes";

describe("textoError", () => {
  it("no distingue correo inexistente de contraseña errada (DT-06)", () => {
    expect(textoError(new ErrorApi(401, "Correo o contraseña incorrectos."))).toBe(
      "Correo o contraseña incorrectos.");
  });
  it("explica el bloqueo por intentos", () => {
    expect(textoError(new ErrorApi(429, "x"))).toMatch(/Espera unos minutos/);
  });
  it("sin respuesta del servidor no culpa al usuario", () => {
    expect(textoError(new TypeError("Failed to fetch"))).toMatch(/conexión/);
  });
});
