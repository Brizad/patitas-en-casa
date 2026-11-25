// Mini encuesta del adoptante (#420): una pregunta por pantalla. Siete preguntas llenan el
// perfil real (las mismas siete casillas de antes, se guardan con guardarPerfil); dos más
// (especie y tamaño) solo filtran lo que se muestra y no viajan al servidor.
import type { Perfil } from "./apiAdopcion";

export type PrefEspecie = "perro" | "gato" | "igual";
export type PrefTamano = "pequeno" | "mediano" | "grande" | "igual";

export interface Respuestas extends Partial<Perfil> {
  especie?: PrefEspecie;
  tamano?: PrefTamano;
}
export type Clave = keyof Respuestas;

export interface Opcion {
  valor: string | number | boolean;
  titulo: string;
  sub: string;
  icono: string; // trazo SVG (viewBox 0 0 24 24)
  fondo: string;
  /** Solo en las horas: el rango que cubre la opción, para no cambiar el número ya guardado. */
  rango?: [number, number];
}
export interface Pregunta { clave: Clave; texto: string; burbuja: string; opciones: Opcion[] }

// Colores pastel de la paleta del prototipo.
export const PASTEL = ["#FFE9A6", "#E4DDFB", "#D7F0DC", "#FBD9E3", "#D6ECFB", "#FFDCC2"];
const [AMARILLO, LILA, MENTA, ROSA, CELESTE, DURAZNO] = PASTEL;

export const ICONO = {
  perro: "M5 9c-2 0-3-3-2-5 2 0 4 1 5 3M19 9c2 0 3-3 2-5-2 0-4 1-5 3M7 8c1-2 3-3 5-3s4 1 5 3c1 3 1 7-1 9-1 1-2 2-4 2s-3-1-4-2c-2-2-2-6-1-9zM10 12h.01M14 12h.01M11 15.5c.6.5 1.4.5 2 0",
  gato: "M5 4l3 4M19 4l-3 4M5 4c-1 4-1 8 1 11 1.5 2.5 3.5 4 6 4s4.5-1.5 6-4c2-3 2-7 1-11M10 12h.01M14 12h.01M12 14.5l-1 1h2zM3 14l4-.5M3 17l4-1.5M21 14l-4-.5M21 17l-4-1.5",
  corazon: "M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.1 0 3.6 1.2 5.2 3 1.6-1.8 3.1-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z",
  casa: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
  apartamento: "M5 21V4h10v17M15 9h4v12M8 8h2M8 12h2M8 16h2M3 21h18",
  finca: "M3 20h18M5 20v-7l5-4 5 4v7M14 9l3-5 4 6M17 20v-6",
  pequeno: "M12 14a3 3 0 1 0 0 6a3 3 0 1 0 0-6zM4 21h16",
  mediano: "M12 10a5 5 0 1 0 0 10a5 5 0 1 0 0-10zM4 21h16",
  grande: "M12 5a7.5 7.5 0 1 0 0 15a7.5 7.5 0 1 0 0-15zM4 21h16",
  patio: "M12 21v-6M8 15h8l-4-11zM3 21h18",
  sinPatio: "M4 21V8l8-5 8 5v13zM9 21v-6h6v6",
  ninos: "M9 7a2.5 2.5 0 1 0 0-5a2.5 2.5 0 1 0 0 5zM17 10a2 2 0 1 0 0-4a2 2 0 1 0 0 4zM5 21v-6l-1-4h10l-1 4v6M15 21v-4l-1-3h6l-1 3v4",
  adultos: "M8 8a3 3 0 1 0 0-6a3 3 0 1 0 0 6zM16 8a3 3 0 1 0 0-6a3 3 0 1 0 0 6zM3 21v-5a5 5 0 0 1 10 0M11 21v-5a5 5 0 0 1 10 0",
  mascotas: "M12 15c-2.5 0-4.5 1.6-4.5 3.4 0 1.3 1 2.1 2.3 2.1.9 0 1.5-.4 2.2-.4s1.3.4 2.2.4c1.3 0 2.3-.8 2.3-2.1 0-1.8-2-3.4-4.5-3.4zM6 12a2 2 0 1 0 0-4a2 2 0 1 0 0 4zM10 8a2 2 0 1 0 0-4a2 2 0 1 0 0 4zM14 8a2 2 0 1 0 0-4a2 2 0 1 0 0 4zM18 12a2 2 0 1 0 0-4a2 2 0 1 0 0 4z",
  solo: "M12 8a3.5 3.5 0 1 0 0-7a3.5 3.5 0 1 0 0 7zM5 22v-4a7 7 0 0 1 14 0v4",
  sol: "M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8z",
  reloj: "M12 7v5l3 2M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z",
  luna: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
  estrella: "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z",
  brote: "M12 21v-8M12 13c0-4 3-7 7-7 0 4-3 7-7 7zM12 15c0-3-2.5-5.5-6-5.5 0 3.5 2.5 5.5 6 5.5z",
  calendario: "M4 6h16v15H4zM4 10h16M8 3v5M16 3v5M9 15l2 2 4-4",
  ahoraNo: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18zM8 12h8",
};

const si = (titulo: string, sub: string, icono: string, fondo = MENTA): Opcion =>
  ({ valor: true, titulo, sub, icono, fondo });
const no = (titulo: string, sub: string, icono: string, fondo = LILA): Opcion =>
  ({ valor: false, titulo, sub, icono, fondo });

export const PREGUNTAS: Pregunta[] = [
  { clave: "especie", texto: "¿Perrito o gatito?", burbuja: "¡Hola! Te ayudo a encontrar a tu compañero.",
    opciones: [
      { valor: "perro", titulo: "Perrito", sub: "Guau, paseos y pelota", icono: ICONO.perro, fondo: AMARILLO },
      { valor: "gato", titulo: "Gatito", sub: "Miau, ronroneos y siestas", icono: ICONO.gato, fondo: LILA },
      { valor: "igual", titulo: "¡Me da igual!", sub: "Quiero conocerlos a todos", icono: ICONO.corazon, fondo: ROSA }] },
  { clave: "tamano", texto: "¿De qué tamaño lo imaginas?", burbuja: "Piensa en cómo será de adulto.",
    opciones: [
      { valor: "pequeno", titulo: "Pequeño", sub: "Cabe en tus brazos", icono: ICONO.pequeno, fondo: MENTA },
      { valor: "mediano", titulo: "Mediano", sub: "Ni muy muy, ni tan tan", icono: ICONO.mediano, fondo: AMARILLO },
      { valor: "grande", titulo: "Grande", sub: "Más amor por kilo", icono: ICONO.grande, fondo: CELESTE },
      { valor: "igual", titulo: "Cualquiera", sub: "El tamaño no importa", icono: ICONO.corazon, fondo: ROSA }] },
  { clave: "vivienda", texto: "¿Dónde vivirá tu nuevo amigo?", burbuja: "Cada uno necesita su espacio.",
    opciones: [
      { valor: "casa", titulo: "Casa", sub: "Con su propia puerta", icono: ICONO.casa, fondo: AMARILLO },
      { valor: "apartamento", titulo: "Apartamento", sub: "Cómodo y acogedor", icono: ICONO.apartamento, fondo: LILA },
      { valor: "finca", titulo: "Finca o campo", sub: "Mucho aire libre", icono: ICONO.finca, fondo: MENTA }] },
  { clave: "tiene_patio", texto: "¿Tiene patio o terraza?", burbuja: "Algunos necesitan correr al aire libre.",
    opciones: [si("Sí, hay patio", "Un espacio afuera para jugar", ICONO.patio),
               no("No hay patio", "Saldremos a pasear", ICONO.sinPatio)] },
  { clave: "hay_ninos", texto: "¿Hay niños en casa?", burbuja: "Algunos se llevan mejor con niños.",
    opciones: [si("Sí, hay niños", "Pequeños en casa", ICONO.ninos, AMARILLO),
               no("No hay niños", "Solo adultos", ICONO.adultos)] },
  { clave: "otros_animales", texto: "¿Ya tienes otras mascotas?", burbuja: "Así sé si le tocará compartir.",
    opciones: [si("Sí, ya tengo", "Otro peludo en casa", ICONO.mascotas),
               no("No, sería el único", "Toda la atención para él", ICONO.solo, CELESTE)] },
  { clave: "horas_solo_al_dia", texto: "¿Cuántas horas pasaría solo al día?",
    burbuja: "Así sé cuánta compañía tendrá.",
    opciones: [
      { valor: 2, rango: [0, 2], titulo: "Casi nunca", sub: "De 0 a 2 horas", icono: ICONO.sol, fondo: ROSA },
      { valor: 5, rango: [3, 6], titulo: "Medio día", sub: "De 3 a 6 horas", icono: ICONO.reloj, fondo: CELESTE },
      { valor: 8, rango: [7, 24], titulo: "Casi todo el día", sub: "7 horas o más", icono: ICONO.luna, fondo: LILA }] },
  { clave: "experiencia", texto: "¿Ya has cuidado perros o gatos?", burbuja: "No pasa nada si es tu primera vez.",
    opciones: [si("Sí, ya he cuidado", "Sé lo que implica", ICONO.estrella, AMARILLO),
               no("Es mi primera vez", "Con ganas de aprender", ICONO.brote, MENTA)] },
  { clave: "acepta_seguimiento", texto: "¿Aceptas las visitas o llamadas del refugio a los 30, 90 y 180 días?",
    burbuja: "¡Última pregunta, ya casi!",
    opciones: [si("Sí, acepto", "Es necesario para poder adoptar", ICONO.calendario, MENTA),
               no("Ahora no", "Podrás mirar, pero no solicitar", ICONO.ahoraNo, DURAZNO)] },
];

const CLAVES_DEL_PERFIL: (keyof Perfil)[] = ["vivienda", "tiene_patio", "hay_ninos",
  "otros_animales", "horas_solo_al_dia", "experiencia", "acepta_seguimiento"];

/** Si ya hay perfil, la encuesta empieza con sus respuestas marcadas. */
export function respuestasDesdePerfil(p: Perfil | null): Respuestas {
  return p ? { ...p } : {};
}

/** El perfil que se guarda; null si falta alguna respuesta del perfil. */
export function perfilDesdeRespuestas(r: Respuestas): Perfil | null {
  if (CLAVES_DEL_PERFIL.some((k) => r[k] === undefined)) return null;
  const p = {} as Record<string, unknown>;
  for (const k of CLAVES_DEL_PERFIL) p[k] = r[k];
  return p as unknown as Perfil;
}

const enRango = (o: Opcion, v: unknown) =>
  o.rango !== undefined && typeof v === "number" && v >= o.rango[0] && v <= o.rango[1];

/** La opción ya marcada en esta pregunta (o -1). */
export function opcionElegida(p: Pregunta, r: Respuestas): number {
  const v = r[p.clave];
  return p.opciones.findIndex((o) => (o.rango ? enRango(o, v) : o.valor === v));
}

/** Guarda la respuesta. En las horas, si se toca el mismo rango que ya estaba, se conserva el
 *  número exacto del perfil (por ejemplo 4 h no se vuelve 5 h por pasar por la encuesta). */
export function responder(r: Respuestas, p: Pregunta, i: number): Respuestas {
  const o = p.opciones[i];
  if (o.rango && enRango(o, r[p.clave])) return { ...r };
  return { ...r, [p.clave]: o.valor };
}

/** «Mi hogar» (arreglos, parte C): cada pregunta del perfil con la respuesta guardada, en
 *  palabras. Especie y tamaño no se guardan en el servidor: no aparecen. */
export function resumenHogar(p: Perfil | null): { pregunta: string; respuesta: string }[] {
  if (!p) return [];
  const r = respuestasDesdePerfil(p);
  return PREGUNTAS.filter((q) => (CLAVES_DEL_PERFIL as string[]).includes(q.clave)).map((q) => {
    const i = opcionElegida(q, r);
    const horas = q.clave === "horas_solo_al_dia" ? ` (${p.horas_solo_al_dia} h)` : "";
    return { pregunta: q.texto, respuesta: i >= 0 ? q.opciones[i].titulo + horas : "—" };
  });
}
