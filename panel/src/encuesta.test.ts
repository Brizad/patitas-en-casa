import { describe, expect, it } from "vitest";
import { PERFIL_VACIO, Perfil } from "./apiAdopcion";
import {
  PREGUNTAS, Respuestas, opcionElegida, perfilDesdeRespuestas, responder, respuestasDesdePerfil,
} from "./encuesta";

const pregunta = (clave: string) => PREGUNTAS.find((p) => p.clave === clave)!;
const indice = (clave: string, valor: unknown) =>
  pregunta(clave).opciones.findIndex((o) => o.valor === valor);

/** Responde toda la encuesta eligiendo, en cada pregunta, la opción con ese valor. */
function contestar(valores: Record<string, unknown>): Respuestas {
  return PREGUNTAS.reduce((r, p) => responder(r, p, indice(p.clave, valores[p.clave])), {} as Respuestas);
}

describe("encuesta → perfil", () => {
  it("pregunta las siete casillas del perfil y dos que solo filtran", () => {
    expect(PREGUNTAS.map((p) => p.clave)).toEqual(["especie", "tamano", "vivienda", "tiene_patio",
      "hay_ninos", "otros_animales", "horas_solo_al_dia", "experiencia", "acepta_seguimiento"]);
    for (const p of PREGUNTAS) expect(p.opciones.length, p.clave).toBeGreaterThanOrEqual(2);
  });

  it("las respuestas llenan el perfil real que se guarda con guardarPerfil", () => {
    const r = contestar({ especie: "gato", tamano: "pequeno", vivienda: "apartamento",
      tiene_patio: false, hay_ninos: true, otros_animales: false, horas_solo_al_dia: 8,
      experiencia: true, acepta_seguimiento: true });
    expect(perfilDesdeRespuestas(r)).toEqual<Perfil>({ vivienda: "apartamento",
      tiene_patio: false, hay_ninos: true, otros_animales: false, horas_solo_al_dia: 8,
      experiencia: true, acepta_seguimiento: true });
  });

  it("especie y tamaño no viajan al servidor", () => {
    const r = contestar({ especie: "perro", tamano: "grande", vivienda: "casa", tiene_patio: true,
      hay_ninos: false, otros_animales: true, horas_solo_al_dia: 2, experiencia: false,
      acepta_seguimiento: false });
    const p = perfilDesdeRespuestas(r)!;
    expect(Object.keys(p).sort()).toEqual(Object.keys(PERFIL_VACIO).sort());
    expect(p).not.toHaveProperty("especie");
    expect(p).not.toHaveProperty("tamano");
  });

  it("sin todas las respuestas del perfil no hay nada que guardar", () => {
    expect(perfilDesdeRespuestas({})).toBeNull();
    expect(perfilDesdeRespuestas({ vivienda: "casa", especie: "gato" })).toBeNull();
    // false también es una respuesta (no hay patio): no cuenta como vacío
    const { acepta_seguimiento: _, ...sinSeguimiento } = { ...PERFIL_VACIO };
    expect(perfilDesdeRespuestas(sinSeguimiento)).toBeNull();
    expect(perfilDesdeRespuestas({ ...PERFIL_VACIO })).toEqual(PERFIL_VACIO);
  });
});

describe("encuesta con un perfil ya guardado", () => {
  const guardado: Perfil = { vivienda: "finca", tiene_patio: true, hay_ninos: false,
    otros_animales: true, horas_solo_al_dia: 4, experiencia: true, acepta_seguimiento: true };

  it("precarga las respuestas y marca la opción de cada pregunta", () => {
    const r = respuestasDesdePerfil(guardado);
    expect(opcionElegida(pregunta("vivienda"), r)).toBe(indice("vivienda", "finca"));
    expect(opcionElegida(pregunta("tiene_patio"), r)).toBe(indice("tiene_patio", true));
    expect(opcionElegida(pregunta("hay_ninos"), r)).toBe(indice("hay_ninos", false));
    expect(pregunta("horas_solo_al_dia").opciones[opcionElegida(pregunta("horas_solo_al_dia"), r)]
      .titulo).toBe("Medio día"); // 4 h está en «de 3 a 6 horas»
    expect(opcionElegida(pregunta("especie"), r)).toBe(-1); // no se guarda en el servidor
    expect(respuestasDesdePerfil(null)).toEqual({});
  });

  it("tocar el mismo rango de horas conserva el número exacto; otro rango lo cambia", () => {
    const r = respuestasDesdePerfil(guardado);
    const horas = pregunta("horas_solo_al_dia");
    const medio = horas.opciones.findIndex((o) => o.titulo === "Medio día");
    expect(responder(r, horas, medio).horas_solo_al_dia).toBe(4);
    const casiNunca = horas.opciones.findIndex((o) => o.titulo === "Casi nunca");
    expect(responder(r, horas, casiNunca).horas_solo_al_dia).toBe(2);
  });

  it("los rangos de horas cubren de 0 a 24 sin huecos", () => {
    for (let h = 0; h <= 24; h++) {
      expect(opcionElegida(pregunta("horas_solo_al_dia"), { horas_solo_al_dia: h }), `${h} h`)
        .toBeGreaterThanOrEqual(0);
    }
  });
});
