import { describe, expect, it } from "vitest";
import { ErrorApi } from "./api";
import { etiquetaEstado, textoError } from "./mensajes";

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

describe("etiquetaEstado", () => {
  it("la falla segura y la baja confianza se nombran, no se esconden", () => {
    expect(etiquetaEstado("sin_clasificar", "alta")).toMatch(/falla segura/);
    expect(etiquetaEstado("requiere_revision", "media")).toMatch(/Requiere revisión/);
    expect(etiquetaEstado("clasificado", "critica")).toBe("Crítica");
  });
});
