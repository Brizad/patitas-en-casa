// Perfil de adopción del animal (#508): estadísticas 1 a 5, tipo calculado por el servidor,
// habilidades de un catálogo fijo y salud (sí, no o sin dato). La salud solo la edita el
// veterinario. El tipo nunca se calcula aquí: la regla vive en app/adopciones/perfil.py.
import { pedir } from "./api";

export type ClaveEstadistica = "energia" | "carino" | "juego" | "paciencia";
export type ClaveSalud = "vacunas" | "esterilizado" | "desparasitado";
export type Estadisticas = Record<ClaveEstadistica, number | null>;
export type Salud = Record<ClaveSalud, boolean | null>;
export type Tipo = "jugueton" | "aventurero" | "tranquilo" | "carinoso" | "guardian";

export interface PerfilAdopcion {
  animal_id: number; nombre: string; estadisticas: Estadisticas; tipo: Tipo | null;
  habilidades: string[]; salud: Salud; catalogo_habilidades?: string[];
}

export const ESTADISTICAS: [ClaveEstadistica, string][] = [
  ["energia", "Energía"], ["carino", "Cariño"], ["juego", "Juego"], ["paciencia", "Paciencia"]];
export const SALUD: [ClaveSalud, string][] = [
  ["vacunas", "Vacunas al día"], ["esterilizado", "Esterilizado"], ["desparasitado", "Desparasitado"]];
/** Nombre y color de cada tipo (pastilla de las cartas). */
export const TIPOS: Record<Tipo, [string, string]> = {
  jugueton: ["Juguetón", "#FFD23F"], aventurero: ["Aventurero", "#FBD9E3"],
  tranquilo: ["Tranquilo", "#D7F0DC"], carinoso: ["Cariñoso", "#E9E2FF"],
  guardian: ["Guardián", "#D6E8F7"],
};

/** Valor de un <select> de salud: "si", "no" o "" (sin dato). */
export const deSalud = (v: boolean | null): string => (v === null ? "" : v ? "si" : "no");
export const aSalud = (v: string): boolean | null => (v === "" ? null : v === "si");
/** Valor de un <select> de estadística: "1" a "5" o "" (sin dato). */
export const aEstadistica = (v: string): number | null => (v === "" ? null : Number(v));

const json = (cuerpo: unknown): RequestInit => ({
  method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
});
const ruta = (id: number, que: string) => `/refugio/animales/${id}/${que}`;

/** 404 si el animal aún no está publicado. */
export const perfilAdopcion = (t: string, id: number) =>
  pedir<PerfilAdopcion>(ruta(id, "perfil-adopcion"), {}, t);
export const guardarPerfilAdopcion = (t: string, id: number, estadisticas: Estadisticas,
                                      habilidades: string[]) =>
  pedir<PerfilAdopcion>(ruta(id, "perfil-adopcion"), json({ estadisticas, habilidades }), t);
/** Solo el veterinario (403 para el coordinador). */
export const guardarSaludAdopcion = (t: string, id: number, salud: Salud) =>
  pedir<PerfilAdopcion>(ruta(id, "salud-adopcion"), json(salud), t);
