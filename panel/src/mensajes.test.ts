import { describe, expect, it } from "vitest";
import { ErrorApi } from "./api";
import {
  etiquetaEstado, faltaJustificacion, mensajeConfirmacion, sugerida, textoAvisos, textoError,
} from "./mensajes";

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

const respuesta = (estado: "pendiente" | "sin_destinatarios" | "no_aplica", programados = 0) =>
  ({ codigo: "K7M2Q9XA", estado: "confirmado", prioridad: "critica" as const, ajustada: false,
     avisos: { programados, estado } });

describe("mensajeConfirmacion (D-05)", () => {
  it("dice pendiente, nunca que el aviso llegó", () => {
    const texto = mensajeConfirmacion(respuesta("pendiente", 2));
    expect(texto).toMatch(/pendiente de envío a 2 rescatistas/);
    expect(texto).not.toMatch(/se avisó|enviado/i);
  });
  it("sin rescatistas disponibles lo dice y anuncia el escalamiento", () => {
    expect(mensajeConfirmacion(respuesta("sin_destinatarios"))).toMatch(/No hay rescatistas/);
  });
  it("media o baja no prometen avisos", () => {
    expect(mensajeConfirmacion({ ...respuesta("no_aplica"), prioridad: "media" })).toMatch(
      /Prioridad media confirmada\. El refugio programará/);
  });
});

describe("justificación (RN-16)", () => {
  it("solo se exige si la prioridad cambia, con 10 caracteres o más", () => {
    expect(faltaJustificacion("alta", "alta", "")).toBe(false);
    expect(faltaJustificacion("alta", "media", "corta")).toBe(true);
    expect(faltaJustificacion("alta", "media", "  123456789  ")).toBe(true);
    expect(faltaJustificacion("alta", "media", "Camina sin dificultad")).toBe(false);
  });
  it("sin clasificar se confirma como alta", () => {
    expect(sugerida("sin_clasificar", "baja")).toBe("alta");
  });
});

describe("textoAvisos", () => {
  const resumen = { pendiente: 1, enviando: 0, enviado: 0, fallido: 0 };
  it("un pendiente que ya falló muestra el motivo y el intento", () => {
    expect(textoAvisos(resumen, [{ estado: "pendiente", intentos: 1,
      ultimo_error: "SMTP: ConnectionRefusedError" }])).toBe(
      "Avisos: 1 pendiente. Último error: SMTP: ConnectionRefusedError (intento 1).");
  });
  it("sin errores solo cuenta", () => {
    expect(textoAvisos({ ...resumen, pendiente: 0, enviado: 2 }, [])).toBe("Avisos: 2 enviado.");
  });
});
