// Flujo «Elige a tu compañero» del adoptante (#420): a qué pantalla se va con cada toque y lo
// que se muestra de cada animal. Todo es puro (sin React ni navegador) para probarlo con vitest.
// Los datos salen del servidor tal cual: el puntaje es el de RF-09 y nada se inventa.
import type { AnimalPublicado, MiSolicitud, Perfil, Recomendado } from "./apiAdopcion";
import { PASTEL, PREGUNTAS, PrefEspecie, Respuestas, responder, respuestasDesdePerfil } from "./encuesta";

export type PantallaAdopcion = "inicio" | "encuesta" | "combinan" | "elegir" | "listo" | "solicitudes";
export type Filtro = "todos" | "perro" | "gato";

export interface EstadoFlujo {
  pantalla: PantallaAdopcion;
  paso: number; // pregunta actual de la encuesta
  respuestas: Respuestas;
  filtro: Filtro;
  elegido: number | null; // animal_id que se mira en «Elige» y en «¡Lo elegiste!»
  desde: PantallaAdopcion; // adónde vuelve «Atrás» desde «Elige»
  guardar: boolean; // la encuesta terminó y falta guardar el perfil
  recien: boolean; // la solicitud se acaba de enviar (confeti)
}

export type Accion =
  | { tipo: "empezar"; perfil: Perfil | null }
  | { tipo: "responder"; opcion: number }
  | { tipo: "guardado" }
  | { tipo: "atras" }
  | { tipo: "verTodos" }
  | { tipo: "ver"; animal: number }
  | { tipo: "filtrar"; filtro: Filtro }
  | { tipo: "mover"; ids: number[]; paso: 1 | -1 }
  | { tipo: "solicitado"; animal: number; recien: boolean }
  | { tipo: "irA"; pantalla: "inicio" | "solicitudes" };

export const INICIAL: EstadoFlujo = { pantalla: "inicio", paso: 0, respuestas: {}, filtro: "todos",
  elegido: null, desde: "inicio", guardar: false, recien: false };

const filtroDe = (e?: PrefEspecie): Filtro => (e === "perro" || e === "gato" ? e : "todos");

export function flujo(s: EstadoFlujo, a: Accion): EstadoFlujo {
  switch (a.tipo) {
    case "empezar": // las del perfil vienen del servidor; especie y tamaño, de esta visita
      return { ...s, pantalla: "encuesta", paso: 0, guardar: false,
               respuestas: { especie: s.respuestas.especie, tamano: s.respuestas.tamano,
                             ...respuestasDesdePerfil(a.perfil) } };
    case "responder": {
      const respuestas = responder(s.respuestas, PREGUNTAS[s.paso], a.opcion);
      if (s.paso < PREGUNTAS.length - 1) return { ...s, respuestas, paso: s.paso + 1 };
      return { ...s, respuestas, pantalla: "combinan", guardar: true,
               filtro: filtroDe(respuestas.especie) };
    }
    case "guardado":
      return { ...s, guardar: false };
    case "atras":
      if (s.pantalla === "encuesta" && s.paso > 0) return { ...s, paso: s.paso - 1 };
      if (s.pantalla === "elegir") return { ...s, pantalla: s.desde };
      return { ...s, pantalla: "inicio" };
    case "verTodos":
      return { ...s, pantalla: "elegir", filtro: "todos", desde: desdeValido(s.pantalla) };
    case "ver":
      return { ...s, pantalla: "elegir", elegido: a.animal, filtro: "todos",
               desde: desdeValido(s.pantalla) };
    case "filtrar":
      return { ...s, filtro: a.filtro };
    case "mover": {
      if (a.ids.length === 0) return s;
      const i = Math.max(0, a.ids.indexOf(actual(a.ids, s.elegido) as number));
      return { ...s, elegido: a.ids[(i + a.paso + a.ids.length) % a.ids.length] };
    }
    case "solicitado":
      return { ...s, pantalla: "listo", elegido: a.animal, recien: a.recien };
    case "irA":
      return { ...s, pantalla: a.pantalla, recien: false };
  }
}

const desdeValido = (p: PantallaAdopcion): PantallaAdopcion =>
  (p === "combinan" || p === "solicitudes" ? p : "inicio");

/** El animal que se muestra: el elegido si sigue en la lista; si no, el primero. */
export function actual(ids: number[], elegido: number | null): number | null {
  return elegido !== null && ids.includes(elegido) ? elegido : (ids[0] ?? null);
}

// ---------- lo que se muestra de cada animal ----------

export function filtrar<T extends AnimalPublicado>(animales: T[], f: Filtro): T[] {
  return f === "todos" ? animales : animales.filter((a) => a.especie === f);
}

export function contar(animales: AnimalPublicado[]): Record<Filtro, number> {
  return { todos: animales.length, perro: filtrar(animales, "perro").length,
           gato: filtrar(animales, "gato").length };
}

/** Los 3 que más combinan (ya vienen ordenados por el puntaje del servidor), filtrados por
 *  especie y tamaño. Si el filtro deja la lista vacía se afloja y se avisa con «ajustado». */
export function mejores(recomendados: Recomendado[], r: Respuestas):
  { lista: Recomendado[]; ajustado: boolean } {
  const especie = (a: Recomendado) => !r.especie || r.especie === "igual" || a.especie === r.especie;
  const tamano = (a: Recomendado) => !r.tamano || r.tamano === "igual" || a.tamano === r.tamano;
  for (const prueba of [(a: Recomendado) => especie(a) && tamano(a), especie]) {
    const lista = recomendados.filter(prueba);
    if (lista.length) return { lista: lista.slice(0, 3), ajustado: prueba === especie };
  }
  return { lista: recomendados.slice(0, 3), ajustado: recomendados.length > 0 };
}

const mayuscula = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/** La razón más fuerte del puntaje, para la tarjeta. */
export const razonCorta = (r: Recomendado) => (r.razones[0] ? mayuscula(r.razones[0]) + "." : "");

export const TAMANO: Record<string, string> = { pequeno: "pequeño", mediano: "mediano", grande: "grande" };
export const fondoDe = (animalId: number) => PASTEL[Math.abs(animalId) % PASTEL.length];
export const especieTexto = (especie: string) => (especie === "gato" ? "Gatito" : "Perrito");

export function edadTexto(meses: number): string {
  if (meses < 12) return `${meses} ${meses === 1 ? "mes" : "meses"}`;
  const anos = Math.floor(meses / 12);
  return `${anos} ${anos === 1 ? "año" : "años"}`;
}

/** Franja «Hoy → De adulto» con la edad y el tamaño que registró el refugio. */
export function hoyYAdulto(a: AnimalPublicado): { hoy: string; adulto: string } {
  const tamano = TAMANO[a.tamano] ?? a.tamano;
  return a.edad_meses < 12
    ? { hoy: `${edadTexto(a.edad_meses)}, aún crece`, adulto: `Tamaño ${tamano}` }
    : { hoy: edadTexto(a.edad_meses), adulto: `Ya es adulto · tamaño ${tamano}` };
}

export interface Estadistica { etiqueta: string; valor: number; texto: string }

/** Barras solo con datos reales de la publicación (y el puntaje del servidor, si lo hay). */
export function estadisticas(a: AnimalPublicado | Recomendado): Estadistica[] {
  const energia = { baja: 33, media: 66, alta: 100 }[a.energia] ?? 0;
  const siNo = (v: boolean) => ({ valor: v ? 100 : 0, texto: v ? "Sí" : "No" });
  const filas: Estadistica[] = [
    { etiqueta: "Energía", valor: energia, texto: mayuscula(a.energia) },
    { etiqueta: "Apto con niños", ...siNo(a.apto_ninos) },
    { etiqueta: "Apto con otros animales", ...siNo(a.apto_otros_animales) },
    { etiqueta: "Necesita patio", ...siNo(a.necesita_patio) },
  ];
  if ("puntaje" in a) filas.push({ etiqueta: "Compatibilidad", valor: a.puntaje, texto: `${a.puntaje} %` });
  return filas;
}

export function insignias(a: AnimalPublicado): string[] {
  return [especieTexto(a.especie), `Tamaño ${TAMANO[a.tamano] ?? a.tamano}`, `Energía ${a.energia}`];
}

// ---------- solicitudes ----------

const ABIERTAS = ["pendiente", "visita"];
export const ESTADO_SOLICITUD: Record<string, string> = { pendiente: "Pendiente",
  visita: "Visita pedida", aprobada: "Aprobada", rechazada: "No aprobada", devuelta: "Devuelta" };

/** La solicitud más reciente de este animal (la abierta primero), si hay. */
export function solicitudDe(mias: MiSolicitud[], animalId: number | null): MiSolicitud | undefined {
  const suyas = mias.filter((s) => s.animal_id === animalId)
    .sort((x, y) => y.creada_en.localeCompare(x.creada_en));
  return suyas.find((s) => ABIERTAS.includes(s.estado)) ?? suyas[0];
}
export const abierta = (s?: MiSolicitud) => !!s && ABIERTAS.includes(s.estado);

export type EstadoPaso = "hecho" | "ahora" | "luego" | "no";
export interface Paso { titulo: string; detalle: string; estado: EstadoPaso }

/** Pasos siguientes según el estado real de la solicitud (nunca se promete lo que no pasó). */
export function pasosSolicitud(estado: string): Paso[] {
  const enviada: Paso = { titulo: "Solicitud enviada", detalle: "El refugio ya la tiene", estado: "hecho" };
  const casa = (e: EstadoPaso, detalle: string): Paso => ({ titulo: "¡A casa!", detalle, estado: e });
  switch (estado) {
    case "pendiente": return [enviada,
      { titulo: "El refugio la revisa", detalle: "Puede pedirte una visita o una charla", estado: "ahora" },
      casa("luego", "Si la aprueban, firmas el compromiso en el refugio")];
    case "visita": return [enviada,
      { titulo: "Visita y charla con el refugio", detalle: "Te contactarán para agendarla", estado: "ahora" },
      casa("luego", "Si la aprueban, firmas el compromiso en el refugio")];
    case "aprobada": return [enviada,
      { titulo: "¡El refugio la aprobó!", detalle: "Ya revisaron tu hogar", estado: "hecho" },
      casa("ahora", "Descarga el compromiso, imprímelo y fírmalo en el refugio")];
    case "rechazada": return [enviada,
      { titulo: "El refugio no la aprobó", detalle: "Puedes elegir a otro compañero", estado: "no" }];
    default: return [enviada,
      { titulo: ESTADO_SOLICITUD[estado] ?? mayuscula(estado), detalle: "Pregunta en el refugio por los detalles", estado: "no" }];
  }
}
