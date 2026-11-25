// Llamadas del coordinador para la adopción (RF-25, RF-27, RF-10). Requieren su sesión.
import { pedir } from "./api";
import { AnimalPublicado, Compatibilidad, Perfil } from "./apiAdopcion";

export interface NuevaPublicacion {
  descripcion: string; tamano: "pequeno" | "mediano" | "grande";
  energia: "baja" | "media" | "alta"; edad_meses: number; apto_ninos: boolean;
  apto_otros_animales: boolean; necesita_patio: boolean;
  // #422: ficha «Elige a tu compañero» (opcional)
  carino: number | null; energia_nivel: number | null; juego: number | null;
  calma: number | null; etiquetas: string[]; peso_kg: number | null;
  peso_adulto_kg: number | null;
}
export interface SolicitudRefugio {
  id: number; animal_id: number; animal: string; adoptante: string; mensaje: string;
  estado: string; creada_en: string; perfil: Perfil | null; razon?: string | null;
  compatibilidad: Compatibilidad | null;
}
export interface Pareja extends Compatibilidad {
  adoptante: string; animal_id: number; animal: string; solicito_este_animal: boolean;
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
/** #422: lo que ya está publicado se carga en el formulario para corregirlo. */
export function desdeCatalogo(a: AnimalPublicado): NuevaPublicacion {
  return { descripcion: a.descripcion, tamano: a.tamano as NuevaPublicacion["tamano"],
    energia: a.energia as NuevaPublicacion["energia"], edad_meses: a.edad_meses,
    apto_ninos: a.apto_ninos, apto_otros_animales: a.apto_otros_animales,
    necesita_patio: a.necesita_patio, carino: a.carino ?? null,
    energia_nivel: a.energia_nivel ?? null, juego: a.juego ?? null, calma: a.calma ?? null,
    etiquetas: a.etiquetas ?? [], peso_kg: a.peso_kg ?? null,
    peso_adulto_kg: a.peso_adulto_kg ?? null };
}

/** Lo que se envía: descripción y etiquetas sin espacios de más; las vacías no van. */
export function paraEnviar(p: NuevaPublicacion): NuevaPublicacion {
  return { ...p, descripcion: p.descripcion.trim(),
           etiquetas: p.etiquetas.map((e) => e.trim()).filter(Boolean).slice(0, 3) };
}

/** Cambia la etiqueta i (de 3) sin perder las demás. */
export function conEtiqueta(etiquetas: string[], i: number, texto: string): string[] {
  const nuevas = [...etiquetas];
  while (nuevas.length <= i) nuevas.push("");
  nuevas[i] = texto;
  return nuevas;
}

/** #422: corrige la publicación (y la ficha) de un animal que sigue disponible. */
export const editarPublicacion = (t: string, animalId: number, p: NuevaPublicacion) =>
  pedir(`/refugio/animales/${animalId}/publicacion`, { ...enviar(p), method: "PUT" }, t);
export const solicitudesRefugio = (t: string) =>
  pedir<SolicitudRefugio[]>("/refugio/solicitudes", {}, t);
/** 409 con el motivo si hay una restricción dura (RN-05) o ya se decidió (RN-11). */
export const decidir = (t: string, id: number, aprobar: boolean, razon?: string) =>
  pedir(`/refugio/solicitudes/${id}/decision`, enviar({ aprobar, razon: razon ?? null }), t);
/** RF-28: propuesta de la jornada (no aprueba nada; RN-16). */
export const propuestaJornada = (t: string) =>
  pedir<Pareja[]>("/refugio/jornada/propuesta", {}, t);
/** RF-27: visita previa (nota). RF-10/RN-13: devolución (motivo). */
export const pedirVisita = (t: string, id: number, texto: string) =>
  pedir(`/refugio/solicitudes/${id}/visita`, enviar({ texto }), t);
export const registrarDevolucion = (t: string, id: number, texto: string) =>
  pedir(`/refugio/solicitudes/${id}/devolucion`, enviar({ texto }), t);
/** RF-25: JPEG, PNG o WebP de hasta 300 KB; el servidor revisa el contenido real. */
export const subirFoto = (t: string, animalId: number, archivo: File) => {
  const datos = new FormData();
  datos.append("foto", archivo);
  return pedir(`/refugio/animales/${animalId}/foto`, { method: "POST", body: datos }, t);
};
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
