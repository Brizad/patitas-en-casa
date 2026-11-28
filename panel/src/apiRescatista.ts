// Llamadas y textos del rescatista (HU-06, RF-15, RF-21, RF-22). Funciones puras aparte de la
// pantalla para poder probarlas con vitest.
import { pedir, Prioridad } from "./api";

export type Resultado = "trasladado" | "atendido_en_sitio" | "no_encontrado" | "fallecido"
  | "veterinaria" | "no_rescatado";

export const NOMBRE_RESULTADO: Record<Resultado, string> = {
  trasladado: "Trasladado al refugio",
  atendido_en_sitio: "Atendido en el sitio",
  no_encontrado: "No encontrado",
  fallecido: "Fallecido",
  veterinaria: "Llevado a veterinaria", // #504
  no_rescatado: "No se pudo rescatar", // #504
};

export interface EstadoRescatista { disponible: boolean; comunas: number[] }

export interface Oferta {
  codigo: string; prioridad: Prioridad; descripcion: string; comuna: number | null;
  escalado: boolean; esperando_desde: string;
  // #496: nivel, más de 72 h sin rescatista, lo que dice el reporte y punto aproximado (~110 m).
  nivel: "urgente" | "alta" | "normal"; atrasado: boolean; especie: string | null;
  estado_animal: string | null; latitud: number | null; longitud: number | null;
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

// --- #498: ubicación mientras va en camino y recorrido de demostración -------------------------

/** Cada cuánto se envía la posición (watchPosition da muchas; se manda una cada 12 s). */
export const INTERVALO_UBICACION_MS = 12_000;

export const compartirUbicacion = (t: string, codigo: string, latitud: number, longitud: number) =>
  pedir(`/rescates/${codigo}/ubicacion`, json({ latitud, longitud }), t);

export const dejarDeCompartir = (t: string, codigo: string) =>
  pedir(`/rescates/${codigo}/ubicacion`, { method: "DELETE" }, t);

/** Solo las cuentas de demostración (el servidor responde 403 a cualquier otra). */
export const simularRecorrido = (t: string, codigo: string) =>
  pedir<{ segundos: number }>(`/rescates/${codigo}/simulacion`, { method: "POST" }, t);

export const esCuentaDemo = (correo: string) => correo.endsWith("@demo.patitas.co");

/** true si ya pasó el intervalo desde el último envío (o nunca se envió). */
export const tocaEnviar = (ultimo: number | null, ahora: number) =>
  ultimo === null || ahora - ultimo >= INTERVALO_UBICACION_MS;

// --- #504: informe del rescate en el sitio -----------------------------------------------

export type Encontrado = "si" | "no_estaba" | "otro_animal";
export type EstadoAnimal = "herido" | "desnutrido" | "enfermo" | "sano" | "asustado_agresivo";
export type Accion = "trasladado" | "atendido_en_sitio" | "veterinaria" | "no_rescatado";

export const NOMBRE_ENCONTRADO: Record<Encontrado, string> = {
  si: "Sí", no_estaba: "No estaba", otro_animal: "Era otro animal",
};
export const NOMBRE_ESTADO_ANIMAL: Record<EstadoAnimal, string> = {
  herido: "Herido", desnutrido: "Desnutrido", enfermo: "Enfermo", sano: "Sano",
  asustado_agresivo: "Asustado o agresivo",
};
export const NOMBRE_ACCION_RESCATE: Record<Accion, string> = {
  trasladado: "Trasladado al refugio", atendido_en_sitio: "Atendido en el sitio",
  veterinaria: "Llevado a veterinaria", no_rescatado: "No se pudo rescatar",
};

export interface InformeEnviado {
  codigo: string; rescatista: string; encontrado: Encontrado; estados: EstadoAnimal[];
  resultado: Resultado; resultado_texto: string; motivo: string | null; nota: string | null;
  creado_en: string; fotos: { id: number; url: string }[];
  foto_reporte: { id: number; url: string } | null;
}

export interface DatosInforme {
  encontrado: Encontrado; estados: EstadoAnimal[]; accion: Accion | null;
  motivo: string; nota: string;
}

/** Lo que falta para poder enviar (las mismas reglas del servidor); null si está completo. */
export function faltaEnInforme(d: DatosInforme, fotos: number): string | null {
  if (d.encontrado !== "no_estaba" && !d.accion) return "Elige qué se hizo con el animal.";
  if (d.encontrado !== "no_estaba" && d.accion === "no_rescatado") {
    const motivo = d.motivo.trim();
    if (motivo.length < 10 || (motivo.match(/\p{L}/gu) ?? []).length < 5) {
      return "Escribe por qué no se pudo rescatar (10 caracteres o más).";
    }
  }
  if (d.encontrado !== "no_estaba" && fotos === 0) return "Adjunta al menos una foto de evidencia.";
  if (fotos > 3) return "Puedes adjuntar hasta 3 fotos.";
  if (d.nota.length > 500) return "La nota puede tener hasta 500 caracteres.";
  return null;
}

/** Un solo envío (multipart): los datos y las fotos ya reducidas. El servidor lo valida todo. */
export function enviarInforme(t: string, codigo: string, d: DatosInforme, fotos: Blob[]) {
  const formulario = new FormData();
  formulario.set("encontrado", d.encontrado);
  d.estados.forEach((e) => formulario.append("estados", e));
  if (d.encontrado !== "no_estaba" && d.accion) formulario.set("accion", d.accion);
  if (d.motivo.trim()) formulario.set("motivo", d.motivo.trim());
  if (d.nota.trim()) formulario.set("nota", d.nota.trim());
  fotos.forEach((f, i) => formulario.append("fotos", f, `evidencia-${i + 1}.jpg`));
  return pedir<InformeEnviado>(`/rescates/${codigo}/informe`, { method: "POST", body: formulario }, t);
}

export const informesRecientes = (t: string) => pedir<InformeEnviado[]>("/rescates/informes", {}, t);
