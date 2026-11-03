// «Mis rescates» del rescatista: lo que aceptó, con llegada, resultado y estado. Funciones puras
// aparte de la pantalla para poder probarlas con vitest.
import { pedir } from "./api";
import { fechaLocal } from "./apiHistorial";
import { NOMBRE_RESULTADO, Resultado } from "./apiRescatista";

export type EstadoDeRescate = "en_camino" | "en_sitio" | "atendido";

export interface FilaRescate {
  codigo: string; aceptado_en: string; actualizado_en: string; // UTC (D-06)
  llego: boolean; llegada_en: string | null; resultado: Resultado | null; estado: EstadoDeRescate;
}

export const NOMBRE_ESTADO_RESCATE: Record<EstadoDeRescate, string> = {
  en_camino: "En camino", en_sitio: "En el sitio", atendido: "Atendido",
};

/** Llegada: la hora guardada; «Sí» si llegó antes de que se guardara la hora; si no, «Aún no». */
export const textoLlegada = (f: FilaRescate) =>
  f.llegada_en ? fechaLocal(f.llegada_en) : f.llego ? "Sí" : "Aún no";
export const textoResultado = (f: FilaRescate) =>
  f.resultado ? NOMBRE_RESULTADO[f.resultado] : "Sin resultado";

export const misRescates = (t: string) => pedir<FilaRescate[]>("/rescates/historial", {}, t);
