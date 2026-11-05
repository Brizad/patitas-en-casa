// Modo piloto de usabilidad (RNF-06, #258): invitar participantes y ver sus resultados.
import { ErrorApi, pedir } from "./api";

export interface Invitacion { participante: string; token: string; enlace: string; vence_en: string }
export interface FilaPiloto { participante: string; segundos: number; sus: number }
export interface ResultadosPiloto { invitados: number; completos: number; filas: FilaPiloto[] }

export const META_SEGUNDOS = 90;
export const META_PORCENTAJE = 80;
export const META_SUS = 70;

export const invitar = (t: string) =>
  pedir<Invitacion>("/admin/piloto/participantes", { method: "POST" }, t);
export const resultadosPiloto = (t: string) =>
  pedir<ResultadosPiloto>("/admin/piloto/resultados", {}, t);

/** El CSV exige sesión: se descarga con el token y se guarda desde un blob local. */
export async function csvPiloto(t: string): Promise<Blob> {
  const r = await fetch("/admin/piloto/resultados.csv", { headers: { Authorization: `Bearer ${t}` } });
  if (!r.ok) throw new ErrorApi(r.status, "No se pudo descargar el CSV.");
  return r.blob();
}

/** Las mismas metas que scripts/operacion/resultados_piloto.py; null sin participantes. */
export function resumenPiloto(filas: FilaPiloto[]) {
  if (filas.length === 0) return null;
  const cumplen = filas.filter((f) => f.segundos <= META_SEGUNDOS).length;
  const porcentaje = Math.round((100 * cumplen) / filas.length);
  const sus = filas.reduce((suma, f) => suma + f.sus, 0) / filas.length;
  return { cumplen, porcentaje, sus, cumpleTiempo: porcentaje >= META_PORCENTAJE,
    cumpleSus: sus >= META_SUS };
}
