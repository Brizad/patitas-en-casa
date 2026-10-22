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

/** RN-16: solo cambiar la prioridad exige justificación (igual que el servidor). */
export function faltaJustificacion(sugerida: Prioridad, elegida: Prioridad, texto: string) {
  return elegida !== sugerida && texto.trim().length < 10;
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
