// Textos que ve el personal. Funciones puras: se prueban sin navegador (mensajes.test.ts).
import { Aviso, ErrorApi, Prioridad, RespuestaConfirmacion } from "./api";

export function textoError(error: unknown): string {
  if (!(error instanceof ErrorApi)) return "No hay conexión con el servidor. Intenta de nuevo.";
  switch (error.estado) {
    case 401: return "Correo o contraseña incorrectos.";
    case 403: return "Tu rol no permite esta acción.";
    case 429: return "Demasiados intentos. Espera unos minutos antes de volver a intentar.";
    default: return error.detalle;
  }
}

export const NOMBRE_PRIORIDAD: Record<string, string> = {
  critica: "Crítica", alta: "Alta", media: "Media", baja: "Baja",
};

/** Lo que el veterinario debe notar primero del estado del triaje (RN-02, RN-03). */
export function etiquetaEstado(estado: string, prioridad: string): string {
  if (estado === "sin_clasificar") return "Sin clasificar · alta por falla segura";
  if (estado === "requiere_revision") return "Requiere revisión (confianza baja)";
  return NOMBRE_PRIORIDAD[prioridad] ?? prioridad;
}

/** La sugerida que confirma «Confirmar»: alta si el triaje falló (RN-03). */
export function sugerida(estado: string, prioridad: Prioridad): Prioridad {
  return estado === "sin_clasificar" ? "alta" : prioridad;
}

/** RN-16 y D-07: solo cambiar la prioridad exige justificación de 10 caracteres o más con
 * al menos 5 letras (igual que el servidor: «..........» no explica nada). */
export function faltaJustificacion(sugerida: Prioridad, elegida: Prioridad, texto: string) {
  const limpio = texto.trim();
  const letras = (limpio.match(/\p{L}/gu) ?? []).length;
  return elegida !== sugerida && (limpio.length < 10 || letras < 5);
}

/** D-05: dice qué se guardó y qué está pendiente; nunca afirma que el aviso ya llegó. */
export function mensajeConfirmacion(r: RespuestaConfirmacion): string {
  const base = `Prioridad ${NOMBRE_PRIORIDAD[r.prioridad].toLowerCase()} confirmada.`;
  const n = r.avisos.programados;
  switch (r.avisos.estado) {
    case "pendiente":
      return `${base} Aviso pendiente de envío a ${n} ${n === 1 ? "rescatista" : "rescatistas"} de la zona.`;
    case "sin_destinatarios":
      return `${base} No hay rescatistas disponibles en la zona: si nadie lo acepta a tiempo, se avisará al coordinador.`;
    default:
      return `${base} El refugio programará la atención.`;
  }
}

export function textoAvisos(resumen: Record<string, number>, avisos: Aviso[] = []): string {
  const partes = Object.entries(resumen).filter(([, n]) => n > 0).map(([e, n]) => `${n} ${e}`);
  if (!partes.length) return "Este reporte no tiene avisos.";
  // Un pendiente que ya falló no es igual a uno nunca intentado: se muestra el motivo.
  const conError = avisos.filter((a) => a.ultimo_error && a.estado !== "enviado");
  const detalle = conError.map((a) => `${a.ultimo_error} (intento ${a.intentos})`).join("; ");
  return `Avisos: ${partes.join(", ")}.${detalle ? ` Último error: ${detalle}.` : ""}`;
}

/** Enlace a Google Maps: con GPS abre el punto exacto; con dirección busca en Cúcuta. */
export function enlaceMapa(u: { latitud: number | null; longitud: number | null;
  direccion: string | null }): string | null {
  const base = "https://www.google.com/maps/search/?api=1&query=";
  if (u.latitud !== null && u.longitud !== null) {
    return base + encodeURIComponent(`${u.latitud},${u.longitud}`);
  }
  const direccion = u.direccion?.trim();
  return direccion ? base + encodeURIComponent(`${direccion}, Cúcuta`) : null;
}

const NOMBRE_INDICADOR: Record<string, string> = {
  recibido: "Recibido", clasificado: "Clasificado por la IA", requiere_revision: "Requiere revisión",
  sin_clasificar: "Sin clasificar", confirmado: "Confirmado por el veterinario",
  descartado: "Descartado", critica: "Crítica", alta: "Alta", media: "Media", baja: "Baja",
  trasladado: "Trasladado al refugio", atendido_en_sitio: "Atendido en el sitio",
  no_encontrado: "No encontrado", fallecido: "Fallecido",
};

/** Clave técnica de un indicador → texto para personas (la clave desconocida se limpia). */
export function nombreIndicador(clave: string): string {
  const texto = NOMBRE_INDICADOR[clave] ?? clave.replace(/_/g, " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export function plural(n: number, singular: string, pluralTexto: string): string {
  return `${n} ${n === 1 ? singular : pluralTexto}`;
}

/** El nombre técnico de la versión → lo que hace, para quien no es de sistemas (#180). */
export function nombreModelo(version: string | null): string {
  if (!version) return "sin sugerencia automática";
  if (version.startsWith("marcha")) return "modelo de marcha del video";
  if (version.includes("tfidf") && version.startsWith("reglas")) {
    return "reglas de urgencia y modelo de texto";
  }
  if (version.includes("tfidf")) return "modelo de texto";
  if (version.startsWith("reglas")) return "reglas de urgencia";
  return "modelo automático";
}

export function nivelConfianza(c: number): string {
  return c >= 0.8 ? "alta" : c >= 0.6 ? "media" : "baja";
}

const prioridadEnTexto = (p: string) => (NOMBRE_PRIORIDAD[p] ?? p).toLowerCase();

/** Por qué el sistema sugiere esa prioridad, en una o dos frases (RN-02, RN-03, RN-06). */
export function explicarSugerencia(estado: string, prioridad: string, confianza: number | null,
                                   version: string | null): string {
  if (estado === "sin_clasificar") {
    return "El sistema no pudo analizar este reporte, así que por seguridad lo trata como "
      + "prioridad alta. Léelo con cuidado y decide tú.";
  }
  if (estado === "requiere_revision") {
    return "El sistema no está seguro de la prioridad (confianza baja). Lee la descripción y "
      + "decide tú.";
  }
  const nivel = confianza === null ? "" : ` con confianza ${nivelConfianza(confianza)} `
    + `(${Math.round(confianza * 100)} %)`;
  return `El sistema sugiere prioridad ${prioridadEnTexto(prioridad)}${nivel}, según `
    + `${nombreModelo(version)}. Tú decides si la confirmas o la cambias.`;
}

/** Las evidencias salen de la API como notas técnicas; aquí se leen como frases. */
export function evidenciaLegible(texto: string): string {
  const senal = texto.match(/^señal '(.+)' -> (\w+)$/);
  if (senal) return `Detectó «${senal[1]}»: indica prioridad ${prioridadEnTexto(senal[2])}`;
  const termino = texto.match(/^«(.+)» apunta a (\w+)$/);
  if (termino) {
    return `La expresión «${termino[1]}» aparece en casos de prioridad ${prioridadEnTexto(termino[2])}`;
  }
  const opinion = texto.match(/^(modelo|reglas) \S+: (\w+) \(([\d.]+)\)$/);
  if (opinion) {
    const quien = opinion[1] === "modelo" ? "El modelo de texto sugería" : "Las reglas de urgencia sugerían";
    return `${quien} prioridad ${prioridadEnTexto(opinion[2])} `
      + `(${Math.round(Number(opinion[3]) * 100)} % de seguridad)`;
  }
  const mas = texto.match(/^se sugiere (\w+): la más grave entre reglas y modelo$/);
  if (mas) {
    return `Se sugiere prioridad ${prioridadEnTexto(mas[1])}: se toma la más grave entre las `
      + "reglas y el modelo";
  }
  return texto;
}

/** «hace 25 min»: cuánto lleva esperando el reporte. `ahora` se inyecta para poder probarla. */
export function haceCuanto(fechaIso: string, ahora: number = Date.now()): string {
  const minutos = Math.floor((ahora - Date.parse(fechaIso)) / 60000);
  if (minutos < 1) return "hace un momento";
  if (minutos < 60) return `hace ${minutos} min`;
  if (minutos < 1440) return `hace ${Math.floor(minutos / 60)} h`;
  return `hace ${Math.floor(minutos / 1440)} días`;
}
