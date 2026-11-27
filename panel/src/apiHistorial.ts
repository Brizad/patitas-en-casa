// Historial del veterinario: lo que confirmó, ajustó o descartó. Funciones puras aparte de la
// pantalla para poder probarlas con vitest.
import { pedir, Prioridad } from "./api";

export type Accion = "confirmado" | "ajustado" | "descartado" | "archivado";

export interface FilaHistorial {
  codigo: string; accion: Accion; fecha: string; // UTC (D-06)
  prioridad_sugerida: Prioridad | null; prioridad_final: Prioridad | null; // null al descartar
  justificacion: string | null; estado: string | null;
}

export const NOMBRE_ACCION: Record<Accion, string> = {
  confirmado: "Confirmado", ajustado: "Ajustado", descartado: "Descartado",
  archivado: "Archivado: no se pudo verificar", // #496
};

/** Estado actual del reporte: solo los dos que deja una decisión del veterinario. */
export const NOMBRE_ESTADO: Record<string, string> = {
  confirmado: "Confirmado", descartado: "Descartado",
};

/** La API manda UTC; aquí se muestra en la hora del navegador (o en `zona`, para probar). */
export function fechaLocal(fechaIso: string, zona?: string): string {
  return new Date(fechaIso).toLocaleString("es-CO", {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    hourCycle: "h23", timeZone: zona,
  });
}

export const historial = (t: string) => pedir<FilaHistorial[]>("/veterinario/historial", {}, t);
