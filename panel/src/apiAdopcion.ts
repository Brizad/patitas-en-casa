// Llamadas y textos de la adopción (fase 3, #85: RF-08, RF-25, RF-27, RF-10, RF-29).
import { ErrorApi, pedir } from "./api";

export interface Perfil {
  vivienda: "casa" | "apartamento" | "finca"; tiene_patio: boolean; hay_ninos: boolean;
  otros_animales: boolean; horas_solo_al_dia: number; experiencia: boolean;
  acepta_seguimiento: boolean;
}
export interface AnimalPublicado {
  animal_id: number; nombre: string; especie: string; descripcion: string; tamano: string;
  energia: string; edad_meses: number; apto_ninos: boolean; apto_otros_animales: boolean;
  necesita_patio: boolean; foto?: string | null; // RF-25: ruta de la foto, si tiene
}
/** RF-09: puntaje 0-100, por qué encaja, qué conversar y restricciones duras (RN-05). */
export interface Compatibilidad {
  puntaje: number; razones: string[]; alertas: string[]; restricciones: string[];
}
export type Recomendado = AnimalPublicado & Compatibilidad;

export interface MiSolicitud { id: number; animal_id: number; estado: string; creada_en: string }

export const PERFIL_VACIO: Perfil = {
  vivienda: "casa", tiene_patio: false, hay_ninos: false, otros_animales: false,
  horas_solo_al_dia: 4, experiencia: false, acepta_seguimiento: false,
};

const json = (method: string, cuerpo: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
});

/** Público: crea la cuenta de adoptante. Sin autorizar los datos el servidor responde 422. */
export const registrarAdoptante = (correo: string, nombre: string, contrasena: string,
                                   autoriza_datos: boolean) =>
  pedir("/adoptantes", json("POST", { correo, nombre, contrasena, autoriza_datos }));

/** null si aún no hay perfil (404). */
export async function miPerfil(t: string): Promise<Perfil | null> {
  try {
    return await pedir<Perfil>("/adoptantes/yo/perfil", {}, t);
  } catch (e) {
    if (e instanceof ErrorApi && e.estado === 404) return null;
    throw e;
  }
}
export const guardarPerfil = (t: string, p: Perfil) =>
  pedir("/adoptantes/yo/perfil", json("PUT", p), t);
export const catalogo = () => pedir<AnimalPublicado[]>("/adopciones/animales");
/** Solo con perfil: ordena por compatibilidad con el hogar y oculta las restricciones. */
export const recomendaciones = (t: string) =>
  pedir<Recomendado[]>("/adopciones/recomendaciones", {}, t);
export const solicitar = (t: string, animal_id: number, mensaje: string) =>
  pedir("/adopciones/solicitudes", json("POST", { animal_id, mensaje }), t);
export const misSolicitudes = (t: string) =>
  pedir<MiSolicitud[]>("/adopciones/solicitudes/mias", {}, t);

/** RF-29: descarga el PDF con el token (un enlace normal no enviaría el encabezado). */
export async function descargarCompromiso(t: string, id: number): Promise<void> {
  const r = await fetch(`/adopciones/solicitudes/${id}/compromiso.pdf`,
                        { headers: { Authorization: `Bearer ${t}` } });
  if (!r.ok) throw new ErrorApi(r.status, "No se pudo descargar el compromiso.");
  const url = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement("a"),
                          { href: url, download: `compromiso-${id}.pdf` });
  a.click();
  URL.revokeObjectURL(url);
}

/** Lo que verá el adoptante, en palabras: no se le muestran códigos internos. */
export function resumenAnimal(a: AnimalPublicado): string {
  const edad = a.edad_meses < 12 ? `${a.edad_meses} meses`
    : `${Math.floor(a.edad_meses / 12)} año${a.edad_meses >= 24 ? "s" : ""}`;
  const extras = [a.apto_ninos ? "convive con niños" : "mejor sin niños",
                  a.apto_otros_animales ? "convive con otros animales" : "mejor solo",
                  a.necesita_patio ? "necesita patio" : ""].filter(Boolean);
  return `${a.especie}, ${edad}, tamaño ${a.tamano}, energía ${a.energia} · ${extras.join(", ")}`;
}
