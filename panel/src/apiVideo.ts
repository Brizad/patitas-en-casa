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
}

export const ESTADOS_VIDEO: Record<EstadoVideo, string> = {
  pendiente: "pendiente: esperando al trabajador de video",
  enviado: "analizando",
  terminado: "listo",
  no_concluyente: "no concluyente: manda la descripción",
  fallido: "no se pudo analizar: manda la descripción",
};

/** null si el reporte no trae video (404). */
export async function analisisVideo(token: string, codigo: string): Promise<AnalisisVideo | null> {
  try {
    return await pedir<AnalisisVideo>(`/reportes/${codigo}/video`, {}, token);
  } catch (e) {
    if (e instanceof ErrorApi && e.estado === 404) return null;
    throw e;
  }
}

/** La tira exige sesión: se descarga con el token y se muestra desde un blob local. */
export async function urlTira(token: string, codigo: string): Promise<string> {
  const respuesta = await fetch(`/reportes/${codigo}/video/tira.png`,
    { headers: { Authorization: `Bearer ${token}` } });
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, "No se pudo cargar la tira.");
  return URL.createObjectURL(await respuesta.blob());
}
