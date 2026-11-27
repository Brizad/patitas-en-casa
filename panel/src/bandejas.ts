// Bandejas del veterinario y del rescatista (#496): textos, colores y distancias. Funciones puras
// para probarlas con vitest. El ORDEN lo decide el servidor (app/reportes/orden.py); aquí solo se
// reordena por cercanía cuando el rescatista comparte su ubicación.

export type Nivel = "urgente" | "alta" | "normal";

export const NOMBRE_NIVEL: Record<Nivel, string> = { urgente: "Urgente", alta: "Alta", normal: "Normal" };
const RANGO_NIVEL: Record<Nivel, number> = { urgente: 0, alta: 1, normal: 2 };

export const SIN_DATO = "—";
export const ZONA_HORARIA = "America/Bogota";

/** Verde < 1 h, amarillo de 1 a 6 h, rojo > 6 h de espera. */
export function colorEspera(desdeIso: string, ahora: number = Date.now()): "verde" | "amarillo" | "rojo" {
  const horas = (ahora - Date.parse(desdeIso)) / 3_600_000;
  return horas < 1 ? "verde" : horas <= 6 ? "amarillo" : "rojo";
}

/** «27 nov 2026, 3:42 p. m.» en la hora de Colombia (para el title y el detalle). */
export function fechaExacta(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
    timeZone: ZONA_HORARIA,
  });
}

/** El mismo día calendario en Colombia (para «Revisados hoy»). */
export function esDeHoy(iso: string, ahora: number = Date.now()): boolean {
  const dia = (t: number) => new Date(t).toLocaleDateString("en-CA", { timeZone: ZONA_HORARIA });
  return dia(Date.parse(iso)) === dia(ahora);
}

export function textoEspecie(especie: string | null): string {
  return especie ? especie.charAt(0).toUpperCase() + especie.slice(1) : SIN_DATO;
}

export const textoZona = (comuna: number | null) => (comuna ? `Comuna ${comuna}` : SIN_DATO);

export interface Punto { latitud: number; longitud: number }

/** Distancia en línea recta (haversine), en metros. */
export function distanciaMetros(a: Punto, b: Punto): number {
  const rad = (g: number) => (g * Math.PI) / 180;
  const dLat = rad(b.latitud - a.latitud);
  const dLon = rad(b.longitud - a.longitud);
  const h = Math.sin(dLat / 2) ** 2
    + Math.cos(rad(a.latitud)) * Math.cos(rad(b.latitud)) * Math.sin(dLon / 2) ** 2;
  return 2 * 6_371_000 * Math.asin(Math.sqrt(h));
}

/** «850 m» o «2,4 km»; sin dato, «—». */
export function textoDistancia(metros: number | null): string {
  if (metros === null || !Number.isFinite(metros)) return SIN_DATO;
  if (metros < 1000) return `${Math.max(10, Math.round(metros / 10) * 10)} m`;
  return `${(metros / 1000).toLocaleString("es-CO", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} km`;
}

export function distanciaA(yo: Punto | null, caso: { latitud: number | null; longitud: number | null }): number | null {
  if (!yo || caso.latitud === null || caso.longitud === null) return null;
  return distanciaMetros(yo, { latitud: caso.latitud, longitud: caso.longitud });
}

/** Con ubicación: nivel y luego cercanía (los que no tienen punto, al final de su nivel). Sin
 *  ubicación: el orden del servidor (nivel y antigüedad) tal cual. */
export function ordenarPorCercania<T extends { nivel: Nivel; latitud: number | null; longitud: number | null }>(
  casos: T[], yo: Punto | null): T[] {
  if (!yo) return casos;
  const lejos = (c: T) => distanciaA(yo, c) ?? Number.POSITIVE_INFINITY;
  return casos.map((c, i) => ({ c, i })).sort((x, y) =>
    RANGO_NIVEL[x.c.nivel] - RANGO_NIVEL[y.c.nivel] || lejos(x.c) - lejos(y.c) || x.i - y.i)
    .map(({ c }) => c);
}
