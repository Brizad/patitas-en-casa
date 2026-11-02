import { describe, expect, it } from "vitest";
import { ErrorApi } from "./api";
import {
  enlaceMapa, etiquetaEstado, evidenciaLegible, explicarSugerencia, haceCuanto, nombreIndicador,
  nombreModelo, plural, faltaJustificacion, mensajeConfirmacion, sugerida, textoAvisos,
  textoError,
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

describe("faltaJustificacion con relleno (D-07)", () => {
  it("rechaza puntos o números aunque tengan 10 caracteres", () => {
    expect(faltaJustificacion("critica", "alta", "..........")).toBe(true);
    expect(faltaJustificacion("critica", "alta", "1234567890")).toBe(true);
    expect(faltaJustificacion("critica", "alta", "Sangra mucho")).toBe(false);
  });
});

describe("enlaceMapa (#172)", () => {
  it("prefiere las coordenadas GPS y si no, la dirección", () => {
    expect(enlaceMapa({ latitud: 7.89, longitud: -72.5, direccion: "Calle 10" }))
      .toBe("https://www.google.com/maps/search/?api=1&query=7.89%2C-72.5");
    expect(enlaceMapa({ latitud: null, longitud: null, direccion: "Calle 10 #5, La Playa" }))
      .toBe("https://www.google.com/maps/search/?api=1&query=Calle%2010%20%235%2C%20La%20Playa%2C%20C%C3%BAcuta");
  });
  it("sin ubicación no hay enlace", () => {
    expect(enlaceMapa({ latitud: null, longitud: null, direccion: null })).toBeNull();
    expect(enlaceMapa({ latitud: null, longitud: null, direccion: "  " })).toBeNull();
  });
});

describe("nombreIndicador y plural (#176)", () => {
  it("traduce las claves técnicas a lenguaje sencillo", () => {
    expect(nombreIndicador("clasificado")).toBe("Clasificado por la IA");
    expect(nombreIndicador("requiere_revision")).toBe("Requiere revisión");
    expect(nombreIndicador("critica")).toBe("Crítica");
    expect(nombreIndicador("trasladado")).toBe("Trasladado al refugio");
    expect(nombreIndicador("hechos")).toBe("Hechos");
  });
  it("una clave desconocida se muestra legible, no con guiones bajos", () => {
    expect(nombreIndicador("vivienda: apartamento")).toBe("Vivienda: apartamento");
    expect(nombreIndicador("algo_nuevo")).toBe("Algo nuevo");
  });
  it("plural respeta el singular", () => {
    expect(plural(1, "perfil", "perfiles")).toBe("1 perfil");
    expect(plural(3, "perfil", "perfiles")).toBe("3 perfiles");
    expect(plural(0, "decisión", "decisiones")).toBe("0 decisiones");
  });
});

describe("explicación de la sugerencia en lenguaje sencillo (#180)", () => {
  it("nunca muestra el nombre técnico del modelo", () => {
    const t = explicarSugerencia("clasificado", "critica", 0.9, "reglas-v0+tfidf-lr-v1");
    expect(t).toMatch(/prioridad crítica/);
    expect(t).toMatch(/confianza alta \(90 %\)/);
    expect(t).toMatch(/Tú decides/);
    expect(t).not.toMatch(/tfidf|lr-v1|reglas-v0/);
  });
  it("explica la baja confianza y la falla segura sin jerga", () => {
    expect(explicarSugerencia("requiere_revision", "media", 0.4, "reglas-v0")).toMatch(
      /no está seguro/);
    expect(explicarSugerencia("sin_clasificar", "alta", null, null)).toMatch(
      /no pudo analizar.*prioridad alta/);
  });
  it("nombra el modelo por lo que hace", () => {
    expect(nombreModelo("reglas-v0+tfidf-lr-v1")).toBe("reglas de urgencia y modelo de texto");
    expect(nombreModelo("marcha-mlp-v1")).toBe("modelo de marcha del video");
    expect(nombreModelo(null)).toBe("sin sugerencia automática");
  });
  it("las evidencias se leen como frases", () => {
    expect(evidenciaLegible("señal 'cojea' -> media")).toBe(
      "Detectó «cojea»: indica prioridad media");
    expect(evidenciaLegible("«se» apunta a critica")).toBe(
      "La expresión «se» aparece en casos de prioridad crítica");
    expect(evidenciaLegible("modelo tfidf-lr-v1: critica (0.90)")).toBe(
      "El modelo de texto sugería prioridad crítica (90 % de seguridad)");
    expect(evidenciaLegible("reglas reglas-v0: alta (0.65)")).toBe(
      "Las reglas de urgencia sugerían prioridad alta (65 % de seguridad)");
    expect(evidenciaLegible("apoya las cuatro patas")).toBe("apoya las cuatro patas");
  });
  it("la hora se dice como una persona", () => {
    const ahora = Date.parse("2026-11-02T12:00:00Z");
    expect(haceCuanto("2026-11-02T11:59:40Z", ahora)).toBe("hace un momento");
    expect(haceCuanto("2026-11-02T11:35:00Z", ahora)).toBe("hace 25 min");
    expect(haceCuanto("2026-11-02T09:00:00Z", ahora)).toBe("hace 3 h");
    expect(haceCuanto("2026-10-30T12:00:00Z", ahora)).toBe("hace 3 días");
    expect(haceCuanto("2026-11-02T11:59:00Z", ahora)).toBe("hace 1 min");
  });
});
