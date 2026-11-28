import { describe, expect, it } from "vitest";
import type { AnimalPublicado, Perfil, Recomendado } from "./apiAdopcion";
import { PREGUNTAS } from "./encuesta";
import {
  EstadoFlujo, INICIAL, actual, contar, edadTexto, estadisticas, filtrar, flujo, hoyYAdulto, insignias, convivencia,
  mejores, pasosSolicitud, razonCorta, resumenCorto, solicitudDe,
} from "./flujoAdopcion";

const animal = (id: number, especie: string, extra: Partial<AnimalPublicado> = {}): AnimalPublicado => ({
  animal_id: id, nombre: `A${id}`, especie, descripcion: "x", tamano: "mediano", energia: "media",
  edad_meses: 24, apto_ninos: true, apto_otros_animales: false, necesita_patio: false, ...extra });
const recomendado = (id: number, especie: string, puntaje: number,
                     extra: Partial<AnimalPublicado> = {}): Recomendado => ({
  ...animal(id, especie, extra), puntaje, razones: ["no exige experiencia previa", "b", "c"],
  alertas: [], restricciones: [] });

const PERFIL: Perfil = { vivienda: "casa", tiene_patio: true, hay_ninos: false,
  otros_animales: false, horas_solo_al_dia: 4, experiencia: true, acepta_seguimiento: true };

describe("navegación entre pantallas", () => {
  it("bienvenida → encuesta → «combinan contigo», y al final pide guardar el perfil", () => {
    let s = flujo(INICIAL, { tipo: "empezar", perfil: null });
    expect(s.pantalla).toBe("encuesta");
    expect(s.paso).toBe(0);
    for (let i = 0; i < PREGUNTAS.length - 1; i++) {
      s = flujo(s, { tipo: "responder", opcion: 0 });
      expect(s.pantalla).toBe("encuesta");
      expect(s.paso).toBe(i + 1);
      expect(s.guardar).toBe(false);
    }
    s = flujo(s, { tipo: "responder", opcion: 0 });
    expect(s.pantalla).toBe("combinan");
    expect(s.guardar).toBe(true);
    expect(s.filtro).toBe("perro"); // respondió «Perrito»
    expect(flujo(s, { tipo: "guardado" }).guardar).toBe(false);
  });

  it("#516: con «Ahora no» al seguimiento no van los matches sino «Adoptar es para siempre»", () => {
    let s = flujo(INICIAL, { tipo: "empezar", perfil: null });
    for (let i = 0; i < PREGUNTAS.length - 1; i++) s = flujo(s, { tipo: "responder", opcion: 0 });
    s = flujo(s, { tipo: "responder", opcion: 1 }); // «Ahora no»
    expect(s.respuestas.acepta_seguimiento).toBe(false);
    expect(s.pantalla).toBe("acompanar");
    expect(s.guardar).toBe(true); // la respuesta se guarda igual en el perfil
  });

  it("#516: «Cambiar» en Mi hogar abre la encuesta en esa pregunta con lo guardado", () => {
    const s = flujo(INICIAL, { tipo: "empezar", perfil: PERFIL, precargar: true, paso: PREGUNTAS.length - 1 });
    expect([s.pantalla, s.paso, s.desde]).toEqual(["encuesta", PREGUNTAS.length - 1, "hogar"]);
    expect(s.respuestas.acepta_seguimiento).toBe(true);
  });

  it("«Atrás» en la encuesta vuelve a la pregunta anterior y en la primera, a la bienvenida", () => {
    let s = flujo(INICIAL, { tipo: "empezar", perfil: null });
    s = flujo(s, { tipo: "responder", opcion: 1 });
    expect(flujo(s, { tipo: "atras" }).paso).toBe(0);
    expect(flujo(flujo(s, { tipo: "atras" }), { tipo: "atras" }).pantalla).toBe("inicio");
  });

  it("«Cambiar mis respuestas» precarga lo guardado y conserva especie y tamaño de la visita", () => {
    const antes: EstadoFlujo = { ...INICIAL, respuestas: { especie: "gato", tamano: "igual" } };
    const s = flujo(antes, { tipo: "empezar", perfil: PERFIL, precargar: true });
    expect(s.respuestas).toMatchObject({ ...PERFIL, especie: "gato", tamano: "igual" });
  });

  it("«¡Empezar!» arranca todo sin marcar, aunque ya haya perfil (arreglos, parte C)", () => {
    const antes: EstadoFlujo = { ...INICIAL, respuestas: { especie: "gato" } };
    expect(flujo(antes, { tipo: "empezar", perfil: PERFIL }).respuestas).toEqual({});
  });

  it("«Mi hogar» → cambiar respuestas → «Atrás» en la primera vuelve a «Mi hogar»", () => {
    let s = flujo(INICIAL, { tipo: "irA", pantalla: "hogar" });
    expect(s.pantalla).toBe("hogar");
    s = flujo(s, { tipo: "empezar", perfil: PERFIL, precargar: true });
    expect(flujo(s, { tipo: "atras" }).pantalla).toBe("hogar");
    expect(flujo(flujo(INICIAL, { tipo: "empezar", perfil: null }), { tipo: "atras" }).pantalla).toBe("inicio");
    expect(flujo({ ...INICIAL, pantalla: "hogar" }, { tipo: "atras" }).pantalla).toBe("inicio");
  });

  it("con perfil se puede ir directo a «combinan» sin repetir la encuesta", () => {
    expect(flujo(INICIAL, { tipo: "irA", pantalla: "combinan" })).toMatchObject({ pantalla: "combinan", guardar: false });
  });

  it("«Ver a todos» y tocar un animal abren «Elige»; «Atrás» vuelve de donde vino", () => {
    const desdeInicio = flujo(INICIAL, { tipo: "verTodos" });
    expect(desdeInicio).toMatchObject({ pantalla: "elegir", filtro: "todos" });
    expect(flujo(desdeInicio, { tipo: "atras" }).pantalla).toBe("inicio");
    const combinan: EstadoFlujo = { ...INICIAL, pantalla: "combinan", filtro: "gato" };
    const viendo = flujo(combinan, { tipo: "ver", animal: 7 });
    expect(viendo).toMatchObject({ pantalla: "elegir", elegido: 7, filtro: "todos" });
    expect(flujo(viendo, { tipo: "atras" }).pantalla).toBe("combinan");
  });

  it("anterior y siguiente dan la vuelta a la lista visible", () => {
    const s: EstadoFlujo = { ...INICIAL, pantalla: "elegir", elegido: 3 };
    const ids = [1, 3, 5];
    expect(flujo(s, { tipo: "mover", ids, paso: 1 }).elegido).toBe(5);
    expect(flujo(s, { tipo: "mover", ids, paso: -1 }).elegido).toBe(1);
    expect(flujo({ ...s, elegido: 5 }, { tipo: "mover", ids, paso: 1 }).elegido).toBe(1);
    expect(flujo({ ...s, elegido: 99 }, { tipo: "mover", ids, paso: 1 }).elegido).toBe(3);
    expect(flujo(s, { tipo: "mover", ids: [], paso: 1 })).toBe(s);
  });

  it("al solicitar se va a «¡Lo elegiste!» y de ahí a la bienvenida o a mis solicitudes", () => {
    const listo = flujo({ ...INICIAL, pantalla: "elegir" }, { tipo: "solicitado", animal: 3, recien: true });
    expect(listo).toMatchObject({ pantalla: "listo", elegido: 3, recien: true });
    expect(flujo(listo, { tipo: "irA", pantalla: "solicitudes" })).toMatchObject(
      { pantalla: "solicitudes", recien: false });
    expect(flujo(listo, { tipo: "irA", pantalla: "inicio" }).pantalla).toBe("inicio");
  });

  it("el animal visible es el elegido si sigue en la lista filtrada; si no, el primero", () => {
    expect(actual([1, 2], 2)).toBe(2);
    expect(actual([1, 2], 9)).toBe(1);
    expect(actual([], 9)).toBeNull();
  });
});

describe("filtros", () => {
  const todos = [animal(1, "perro"), animal(2, "gato"), animal(3, "perro")];
  it("Todos, Perritos y Gatitos, con su conteo", () => {
    expect(filtrar(todos, "todos")).toHaveLength(3);
    expect(filtrar(todos, "perro").map((a) => a.animal_id)).toEqual([1, 3]);
    expect(filtrar(todos, "gato").map((a) => a.animal_id)).toEqual([2]);
    expect(contar(todos)).toEqual({ todos: 3, perro: 2, gato: 1 });
  });

  it("los 3 que más combinan respetan el orden del servidor y las preferencias", () => {
    const lista = [recomendado(1, "perro", 90, { tamano: "grande" }), recomendado(2, "gato", 85),
      recomendado(3, "perro", 80), recomendado(4, "perro", 70), recomendado(5, "perro", 60)];
    expect(mejores(lista, {}).lista.map((a) => a.animal_id)).toEqual([1, 2, 3]);
    expect(mejores(lista, { especie: "perro" }).lista.map((a) => a.animal_id)).toEqual([1, 3, 4]);
    expect(mejores(lista, { especie: "perro", tamano: "mediano" })).toEqual(
      { lista: [lista[2], lista[3], lista[4]], ajustado: false });
  });

  it("si el filtro deja la lista vacía, se afloja y lo dice", () => {
    const lista = [recomendado(1, "perro", 90), recomendado(2, "perro", 80)];
    const soloEspecie = mejores(lista, { especie: "perro", tamano: "pequeno" });
    expect(soloEspecie).toMatchObject({ ajustado: true });
    expect(soloEspecie.lista).toHaveLength(2);
    expect(mejores(lista, { especie: "gato" })).toMatchObject({ ajustado: true });
    expect(mejores([], { especie: "gato" })).toEqual({ lista: [], ajustado: false });
  });
});

describe("lo que se muestra de cada animal", () => {
  it("las 4 barras del prototipo salen de la ficha del refugio, con sus colores", () => {
    const toby = animal(1, "perro", { carino: 95, energia_nivel: 92, juego: 90, calma: 38 });
    expect(estadisticas(toby)).toEqual([
      { etiqueta: "Cariño", valor: 95, texto: "95", color: "#E8508A" },
      { etiqueta: "Energía", valor: 92, texto: "92", color: "#F2A93B" },
      { etiqueta: "Juego", valor: 90, texto: "90", color: "#7A5AF8" },
      { etiqueta: "Calma", valor: 38, texto: "38", color: "#3FA66B" }]);
  });

  it("sin ficha no se inventan barras; el puntaje del servidor se mantiene", () => {
    expect(estadisticas(animal(1, "perro"))).toEqual([]);
    expect(estadisticas(animal(1, "perro", { carino: 0, juego: null })).map((e) => e.etiqueta))
      .toEqual(["Cariño"]); // 0 es un dato; null no
    const conPuntaje = estadisticas(recomendado(1, "gato", 72));
    expect(conPuntaje).toEqual([{ etiqueta: "Compatibilidad", valor: 72, texto: "72 %", color: "#3B82C4" }]);
  });

  it("con quién convive se dice siempre", () => {
    expect(convivencia(animal(1, "perro", { apto_otros_animales: false, necesita_patio: true })))
      .toEqual(["Convive con niños", "Mejor sin otros animales", "Necesita patio"]);
  });

  it("la razón corta es la más fuerte del servidor, en mayúscula", () => {
    expect(razonCorta(recomendado(1, "gato", 80))).toBe("No exige experiencia previa.");
    expect(razonCorta({ ...recomendado(1, "gato", 80), razones: [] })).toBe("");
  });

  it("resume especie, edad y tamaño en una línea", () => {
    expect(resumenCorto(animal(1, "gato", { edad_meses: 30, tamano: "pequeno" })))
      .toBe("Gatito · 2 años · tamaño pequeño");
  });

  it("edad y franja «Hoy → De adulto»", () => {
    expect(edadTexto(1)).toBe("1 mes");
    expect(edadTexto(8)).toBe("8 meses");
    expect(edadTexto(12)).toBe("1 año");
    expect(edadTexto(30)).toBe("2 años");
    expect(hoyYAdulto(animal(1, "perro", { edad_meses: 4, tamano: "grande" })))
      .toEqual({ hoy: "4 meses", adulto: "Grande" });
    expect(hoyYAdulto(animal(1, "perro", { edad_meses: 3, tamano: "grande", peso_kg: 8, peso_adulto_kg: 35 })))
      .toEqual({ hoy: "3 meses · 8 kg", adulto: "Grande · ~35 kg" });
    expect(hoyYAdulto(animal(1, "gato", { edad_meses: 12, peso_kg: 3.5, peso_adulto_kg: 4.5 })))
      .toEqual({ hoy: "1 año · 3,5 kg", adulto: "Ya es adulto · ~4,5 kg" });
    expect(hoyYAdulto(animal(1, "gato", { edad_meses: 36, tamano: "pequeno" })))
      .toEqual({ hoy: "3 años", adulto: "Ya es adulto · tamaño pequeño" });
  });
});

describe("solicitudes", () => {
  it("los pasos siguen el estado real de la solicitud", () => {
    expect(pasosSolicitud("pendiente").map((p) => p.estado)).toEqual(["hecho", "ahora", "luego"]);
    expect(pasosSolicitud("visita")[1].titulo).toMatch(/Visita/);
    expect(pasosSolicitud("aprobada").map((p) => p.estado)).toEqual(["hecho", "hecho", "ahora"]);
    expect(pasosSolicitud("rechazada").map((p) => p.estado)).toEqual(["hecho", "no"]);
    expect(pasosSolicitud("devuelta")[1].titulo).toBe("Devuelta");
  });

  it("la solicitud de un animal es la abierta o, si no hay, la más reciente", () => {
    const mias = [
      { id: 1, animal_id: 5, estado: "rechazada", creada_en: "2026-11-01T00:00:00Z" },
      { id: 2, animal_id: 5, estado: "pendiente", creada_en: "2026-11-02T00:00:00Z" },
      { id: 3, animal_id: 6, estado: "rechazada", creada_en: "2026-11-01T00:00:00Z" },
      { id: 4, animal_id: 6, estado: "aprobada", creada_en: "2026-11-03T00:00:00Z" }];
    expect(solicitudDe(mias, 5)?.id).toBe(2);
    expect(solicitudDe(mias, 6)?.id).toBe(4);
    expect(solicitudDe(mias, 7)).toBeUndefined();
  });
});

describe("insignias", () => {
  it("son las etiquetas del refugio (máximo 3) si las hay", () => {
    expect(insignias(animal(1, "perro", { etiquetas: ["Juguetón", "Guardián", "Vacunado", "x"] })))
      .toEqual(["Juguetón", "Guardián", "Vacunado"]);
  });
  it("sin etiquetas, solo dicen lo que registró el refugio", () => {
    expect(insignias(animal(1, "perro", { energia: "alta", apto_ninos: true, apto_otros_animales: false,
      necesita_patio: true }))).toEqual(["Energía alta", "Convive con niños", "Necesita patio"]);
    expect(insignias(animal(2, "gato", { apto_ninos: false, apto_otros_animales: true })))
      .toEqual(["Energía media", "Convive con otros animales", "Sin patio está bien"]);
  });
});
