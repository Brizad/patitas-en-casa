// Análisis de video del reporte (#125, RF-03, RF-19): lo que devolvió el trabajador local.
import { ErrorApi, pedir } from "./api";

export type EstadoVideo = "pendiente" | "enviado" | "terminado" | "no_concluyente" | "fallido";

export interface AnalisisVideo {
  estado: EstadoVideo;
  prioridad: string | null;
  confianza: number | null;
  evidencias: string[];
  medidas: Record<string, number | string | null>;
  discrepancia: boolean;
  motivo: string | null;
  version_modelo: string | null;
  tiene_tira: boolean;
  tiene_vista: boolean;
}

export const ESTADOS_VIDEO: Record<EstadoVideo, string> = {
  pendiente: "en espera de análisis",
  enviado: "analizando",
  terminado: "listo",
  no_concluyente: "no concluyente",
  fallido: "no se pudo analizar",
};

/** #231: mientras el video espera o se analiza, el panel vuelve a preguntar cada 15 s. */
export const ESPERA_ACTUALIZAR_MS = 15000;
export function sigueAnalizando(estado: EstadoVideo): boolean {
  return estado === "pendiente" || estado === "enviado";
}

/** #231: qué decir de la vista previa cuando no se puede mostrar (null: nada que decir). */
export function notaDeVista(analisis: AnalisisVideo, falloAlCargar: boolean): string | null {
  if (analisis.tiene_vista) {
    return falloAlCargar ? "No se pudo cargar la vista previa del video. Vuelve a abrir el " +
      "reporte; si sigue igual, avisa al administrador." : null;
  }
  if (analisis.estado === "terminado" || analisis.estado === "no_concluyente") {
    const motivo = analisis.medidas.sin_vista;
    if (typeof motivo === "string" && motivo) {
      return `Este análisis no trae vista previa: ${motivo}.`;
    }
    // Desde la versión 1.3.0 el equipo de análisis siempre dice su versión y el motivo.
    return "Este análisis no trae vista previa del video (el equipo que analiza no la generó " +
      "o ya se borró)." + (analisis.medidas.version_nodo ? "" :
      " Lo analizó un equipo con una versión antigua: pídele al administrador que lo actualice.");
  }
  return null;
}

/** #231: el equipo (nodo) que analiza los videos: ¿está encendido y con el código al día? */
export interface EstadoNodo {
  activado: boolean;
  version_minima: string;
  ultimo_contacto: string | null;
  segundos_sin_contacto: number | null;
  version: string | null;
  analizando: boolean;
  en_linea: boolean;
  al_dia: boolean | null;
}

/** null si no se pudo saber (una API anterior, sin red): la pantalla sigue igual. */
export async function estadoNodo(token: string): Promise<EstadoNodo | null> {
  try {
    return await pedir<EstadoNodo>("/video/nodo", {}, token);
  } catch {
    return null;
  }
}

export function haceCuanto(segundos: number): string {
  if (segundos < 60) return "hace menos de 1 min";
  if (segundos < 3600) return `hace ${Math.floor(segundos / 60)} min`;
  return `hace ${Math.floor(segundos / 3600)} h`;
}

/** Qué decirle al veterinario mientras el video espera (null: nada que decir). */
export function notaDelNodo(nodo: EstadoNodo | null, analisis: AnalisisVideo): string | null {
  if (!nodo || !nodo.activado || !sigueAnalizando(analisis.estado)) return null;
  if (!nodo.en_linea) {
    const cuando = nodo.segundos_sin_contacto === null ? "no ha respondido desde que el " +
      "servidor arrancó" : `respondió por última vez ${haceCuanto(nodo.segundos_sin_contacto)}`;
    return `El equipo que analiza los videos está apagado (${cuando}). El análisis llegará ` +
      "cuando lo enciendan; decide con la descripción.";
  }
  if (nodo.al_dia === false) {
    return "El equipo que analiza los videos corre una versión antigua" +
      (nodo.version ? ` (${nodo.version})` : "") + ": puede que el análisis llegue sin vista " +
      "previa. Pídele al administrador que lo actualice.";
  }
  return null;
}

/** null si el reporte no trae video (404). */
export async function analisisVideo(token: string, codigo: string): Promise<AnalisisVideo | null> {
  try {
    return await pedir<AnalisisVideo>(`/reportes/${codigo}/video`, {}, token);
  } catch (e) {
    if (e instanceof ErrorApi && e.estado === 404) return null;
    throw e;
  }
}

/** Vista previa del video (480p, con el esqueleto dibujado, #214). Un <video> no puede mandar
 *  el token, así que se descarga (5 MB o menos) y se reproduce desde un blob local. */
export async function urlVista(token: string, codigo: string): Promise<string> {
  const respuesta = await fetch(`/reportes/${codigo}/video/vista.mp4`,
    { headers: { Authorization: `Bearer ${token}` } });
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, "No se pudo cargar el video.");
  return URL.createObjectURL(await respuesta.blob());
}

/** La tira exige sesión: se descarga con el token y se muestra desde un blob local. */
export async function urlTira(token: string, codigo: string): Promise<string> {
  const respuesta = await fetch(`/reportes/${codigo}/video/tira.png`,
    { headers: { Authorization: `Bearer ${token}` } });
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, "No se pudo cargar la tira.");
  return URL.createObjectURL(await respuesta.blob());
}
