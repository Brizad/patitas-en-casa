// Lo que muestra cada carta de «Adoptar» (#508). Puro, para probarlo con vitest. Todo sale de
// la ficha real que manda el servidor: lo que no viene no se dibuja (nada por defecto).
import type { AnimalPublicado } from "./apiAdopcion";
import { ClaveSalud, ESTADISTICAS, TIPOS } from "./apiPerfilAdopcion";
import { TAMANO, edadTexto } from "./flujoAdopcion";

const COLOR_BARRA = { energia: "#E8508A", carino: "#9B83FA", juego: "#FFD23F", paciencia: "#7FCB95" };
const SALUD_CORTA: [ClaveSalud, string, string][] = [
  ["vacunas", "Vacunas", "Vacunas al día"], ["esterilizado", "Esteriliz.", "Esterilizado"],
  ["desparasitado", "Desparas.", "Desparasitado"]];

const mayuscula = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/** «Perro · Mediano · 2 años». */
export const metaCarta = (a: AnimalPublicado) => [
  a.especie === "gato" ? "Gato" : "Perro", mayuscula(TAMANO[a.tamano] ?? a.tamano), edadTexto(a.edad_meses),
].join(" · ");

/** Nombre y color de la pastilla del tipo; null si no hay tipo. */
export const tipoCarta = (a: AnimalPublicado) => (a.tipo ? TIPOS[a.tipo] : null);

export interface Barra { nombre: string; valor: number; color: string }
/** Solo las estadísticas con dato, de 1 a 5. */
export const barrasCarta = (a: AnimalPublicado): Barra[] => ESTADISTICAS.flatMap(([clave, nombre]) => {
  const valor = a.estadisticas?.[clave];
  return valor == null ? [] : [{ nombre, valor, color: COLOR_BARRA[clave] }];
});

export interface Insignia { corto: string; largo: string; si: boolean }
/** Salud con dato: ✓ verde si sí, gris si no. Sin dato no sale. */
export const saludCarta = (a: AnimalPublicado): Insignia[] => SALUD_CORTA.flatMap(([clave, corto, largo]) => {
  const valor = a.salud?.[clave];
  return valor == null ? [] : [{ corto, largo, si: valor }];
});

/** El mejor match en el centro: [2.º, 1.º, 3.º] (los que haya). */
export function trio<T>(mejores: T[]): T[] {
  const [primero, segundo, tercero] = mejores;
  return [segundo, primero, tercero].filter((x): x is T => x !== undefined);
}
