// Llamadas del coordinador para la adopción (RF-25, RF-27, RF-10). Requieren su sesión.
import { pedir } from "./api";
import { Perfil } from "./apiAdopcion";

export interface NuevaPublicacion {
  descripcion: string; tamano: "pequeno" | "mediano" | "grande";
  energia: "baja" | "media" | "alta"; edad_meses: number; apto_ninos: boolean;
  apto_otros_animales: boolean; necesita_patio: boolean;
}
export interface SolicitudRefugio {
  id: number; animal_id: number; animal: string; adoptante: string; mensaje: string;
  estado: string; creada_en: string; perfil: Perfil | null;
}
export interface SeguimientoRefugio {
  id: number; dia: number; programado_para: string; realizado_en: string | null;
  nota: string | null; vencido: boolean; animal: string; adoptante: string;
}

const enviar = (cuerpo: unknown): RequestInit => ({
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
});

export const publicar = (t: string, animalId: number, p: NuevaPublicacion) =>
  pedir(`/refugio/animales/${animalId}/publicacion`, enviar(p), t);
export const solicitudesRefugio = (t: string) =>
  pedir<SolicitudRefugio[]>("/refugio/solicitudes", {}, t);
/** 409 con el motivo si hay una restricción dura (RN-05) o ya se decidió (RN-11). */
export const decidir = (t: string, id: number, aprobar: boolean, razon?: string) =>
  pedir(`/refugio/solicitudes/${id}/decision`, enviar({ aprobar, razon: razon ?? null }), t);
export const seguimientosRefugio = (t: string) =>
  pedir<SeguimientoRefugio[]>("/refugio/seguimientos", {}, t);
export const registrarSeguimiento = (t: string, id: number, nota: string) =>
  pedir(`/refugio/seguimientos/${id}`, enviar({ nota }), t);

/** Perfil del adoptante en una línea, para decidir sin abrir otra pantalla. */
export function resumenPerfil(p: Perfil | null): string {
  if (!p) return "Sin perfil";
  const datos = [p.vivienda, p.tiene_patio ? "con patio" : "sin patio",
                 p.hay_ninos ? "hay niños" : "sin niños",
                 p.otros_animales ? "otros animales" : "sin otros animales",
                 `${p.horas_solo_al_dia} h solo al día`,
                 p.experiencia ? "con experiencia" : "sin experiencia"];
  return datos.join(" · ");
}
