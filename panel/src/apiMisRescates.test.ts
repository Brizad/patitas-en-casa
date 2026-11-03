import { describe, expect, it } from "vitest";
import { fechaLocal } from "./apiHistorial";
import { FilaRescate, NOMBRE_ESTADO_RESCATE, textoLlegada, textoResultado } from "./apiMisRescates";

const base: FilaRescate = {
  codigo: "AAAA0001", aceptado_en: "2026-10-15T09:00:00+00:00",
  actualizado_en: "2026-10-15T09:00:00+00:00", llego: false, llegada_en: null,
  resultado: null, estado: "en_camino",
};

describe("mis rescates", () => {
  it("la llegada y el resultado se leen en español", () => {
    expect(textoLlegada(base)).toBe("Aún no");
    // Rescate anterior a la columna: llegó pero no hay hora guardada.
    expect(textoLlegada({ ...base, llego: true })).toBe("Sí");
    expect(textoResultado(base)).toBe("Sin resultado");
    const atendido: FilaRescate = { ...base, llego: true, resultado: "trasladado",
                                    estado: "atendido" };
    expect(textoLlegada({ ...atendido, llegada_en: "2026-10-15T09:20:00+00:00" }))
      .toBe(fechaLocal("2026-10-15T09:20:00+00:00"));
    expect(textoResultado(atendido)).toBe("Trasladado al refugio");
  });
  it("cada estado del historial tiene nombre", () => {
    expect(Object.keys(NOMBRE_ESTADO_RESCATE)).toEqual(["en_camino", "en_sitio", "atendido"]);
  });
});
