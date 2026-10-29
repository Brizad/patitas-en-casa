// Llamadas y textos del refugio (RF-06, RF-07, RN-04). Funciones puras aparte para vitest.
import { pedir } from "./api";

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

/** Solo el coordinador (403 para el veterinario); 409 si no hay cupo (RN-04). */
export const registrarIngreso = (t: string, ingreso: Ingreso) =>
  pedir<{ ocupacion: string }>("/refugio/ingresos", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ingreso),
  }, t);
