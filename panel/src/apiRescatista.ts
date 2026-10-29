// Llamadas y textos del rescatista (HU-06, RF-15, RF-21, RF-22). Funciones puras aparte de la
// pantalla para poder probarlas con vitest.
import { pedir, Prioridad } from "./api";

export type Resultado = "trasladado" | "atendido_en_sitio" | "no_encontrado" | "fallecido";

export const NOMBRE_RESULTADO: Record<Resultado, string> = {
  trasladado: "Trasladado al refugio",
  atendido_en_sitio: "Atendido en el sitio",
  no_encontrado: "No encontrado",
  fallecido: "Fallecido",
};

export interface EstadoRescatista { disponible: boolean; comunas: number[] }

export interface Oferta {
  codigo: string; prioridad: Prioridad; descripcion: string; comuna: number | null;
  escalado: boolean; esperando_desde: string;
}

export interface MiRescate {
  codigo: string; estado: "en_camino" | "en_sitio"; prioridad: Prioridad; descripcion: string;
  ubicacion: { latitud: number | null; longitud: number | null; direccion: string | null;
               comuna: number | null };
}

export function nombreComunas(comunas: number[]): string {
  if (!comunas.length) return "Toda la ciudad";
  return `Comunas ${[...comunas].sort((a, b) => a - b).join(", ")}`;
}

const json = (cuerpo: unknown): RequestInit => ({
  method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
});

export const miEstado = (t: string) => pedir<EstadoRescatista>("/rescatistas/yo", {}, t);
export const cambiarDisponibilidad = (t: string, disponible: boolean) =>
  pedir("/rescatistas/yo/disponibilidad", json({ disponible }), t);
export const cambiarZona = (t: string, comunas: number[]) =>
  pedir("/rescatistas/yo/zona", json({ comunas }), t);
export const ofertas = (t: string) => pedir<Oferta[]>("/rescates/ofertas", {}, t);
export const miRescate = (t: string) => pedir<MiRescate | null>("/rescates/mio", {}, t);

/** aceptar, llegue o liberar: el servidor valida el paso (409 si no corresponde, RN-08). */
export const paso = (t: string, codigo: string, accion: "aceptar" | "llegue" | "liberar") =>
  pedir(`/rescates/${codigo}/${accion}`, { method: "POST" }, t);

export const registrarResultado = (t: string, codigo: string, resultado: Resultado) =>
  pedir(`/rescates/${codigo}/resultado`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resultado }),
  }, t);
