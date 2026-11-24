// Llamadas y textos del refugio (RF-06, RF-07, RN-04). Funciones puras aparte para vitest.
import { ErrorApi, pedir } from "./api";
import { textoError } from "./mensajes";

export interface Ocupacion { ocupacion: string; porcentaje: number }
export interface Ingreso {
  nombre: string; especie: "perro" | "gato"; estado_salud: string;
  vacunado: boolean; esterilizado: boolean;
}

export const ALERTA_PORCENTAJE = 90; // RN-04: igual que ALERTA_OCUPACION en app/config.py

/** Nivel de la barra de ocupación: «alerta» desde el 90 % y «lleno» sin cupos (RN-04). */
export function nivelOcupacion(porcentaje: number): "normal" | "alerta" | "lleno" {
  if (porcentaje >= 100) return "lleno";
  return porcentaje >= ALERTA_PORCENTAJE ? "alerta" : "normal";
}

export const ocupacion = (t: string) => pedir<Ocupacion>("/refugio/ocupacion", {}, t);

/** Cuerpo del ingreso: nombre y salud recortados; «reporte» solo si se escribió un código. */
export function cuerpoIngreso(ingreso: Ingreso, codigo: string): Ingreso & { reporte?: string } {
  const cuerpo: Ingreso & { reporte?: string } = { ...ingreso, nombre: ingreso.nombre.trim(),
    estado_salud: ingreso.estado_salud.trim() };
  if (codigo.trim()) cuerpo.reporte = codigo.trim();
  return cuerpo;
}

/** Texto del error al registrar: 409 sin cupos (RN-04); 422 con código = el reporte no existe. */
export function errorIngreso(e: unknown, hayCodigo: boolean): string {
  if (e instanceof ErrorApi && e.estado === 409)
    return "El refugio no tiene cupos: el ingreso no se registró.";
  if (e instanceof ErrorApi && e.estado === 422 && hayCodigo && /reporte/i.test(e.detalle))
    return "No existe un reporte con ese código. Revisa el código o déjalo vacío.";
  return textoError(e);
}

/** Solo el coordinador (403 para el veterinario); 409 si no hay cupo (RN-04); 422 si el
 *  «reporte» (código opcional, avisa al ciudadano) no existe. */
export const registrarIngreso = (t: string, ingreso: Ingreso & { reporte?: string }) =>
  pedir<{ ocupacion: string }>("/refugio/ingresos", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ingreso),
  }, t);

// --- Fase 2 (#75): fichas, historial y egresos -----------------------------------------
export type TipoNota = "observacion" | "tratamiento" | "vacuna" | "procedimiento";
export type MotivoEgreso = "adopcion" | "traslado" | "fallecimiento" | "devuelto";

export const TIPOS_NOTA: Record<TipoNota, string> = {
  observacion: "Observación", tratamiento: "Tratamiento", vacuna: "Vacuna",
  procedimiento: "Procedimiento",
};
export const MOTIVOS_EGRESO: Record<MotivoEgreso, string> = {
  adopcion: "Adopción", traslado: "Traslado", fallecimiento: "Fallecimiento",
  devuelto: "Devuelto a su familia",
};

export interface Nota { tipo: TipoNota; texto: string; autor: string; registrada_en: string }
export interface FichaAnimal {
  id: number; nombre: string; especie: string; estado_salud: string; vacunado: boolean;
  esterilizado: boolean; ingresado_en: string; egresado_en: string | null;
  motivo_egreso: MotivoEgreso | null; historial: Nota[];
}

export const animales = (t: string) => pedir<FichaAnimal[]>("/refugio/animales", {}, t);
export const ficha = (t: string, id: number) =>
  pedir<FichaAnimal>(`/refugio/animales/${id}`, {}, t);

const enviar = (cuerpo: unknown): RequestInit => ({
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
});

/** Solo el veterinario (403 si no); el historial solo crece. */
export const agregarNota = (t: string, id: number, tipo: TipoNota, texto: string) =>
  pedir(`/refugio/animales/${id}/historial`, enviar({ tipo, texto }), t);

/** Solo el coordinador; 409 si ya egresó. Libera el cupo (RF-26). */
export const egresar = (t: string, id: number, motivo: MotivoEgreso) =>
  pedir<{ ocupacion: string }>(`/refugio/animales/${id}/egreso`, enviar({ motivo }), t);
