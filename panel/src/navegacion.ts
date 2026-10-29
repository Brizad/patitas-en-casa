// Qué pantallas ve cada rol (fase 1, #67). El servidor es quien decide (401/403): esto solo
// evita mostrar botones que siempre fallarían. Función pura: se prueba sin navegador.

export type Pantalla = "cola" | "rescates" | "refugio" | "administracion" | "adopcion"
  | "adopciones" | "indicadores";

export const NOMBRE_PANTALLA: Record<Pantalla, string> = {
  cola: "Cola de triaje",
  rescates: "Mis rescates",
  refugio: "Refugio",
  administracion: "Administración",
  adopcion: "Adopción",
  adopciones: "Adopciones",
  indicadores: "Indicadores",
};

const POR_ROL: Record<string, Pantalla[]> = {
  veterinario: ["cola", "refugio"],
  coordinador: ["refugio", "adopciones", "cola", "indicadores"],
  rescatista: ["rescates"],
  administrador: ["administracion", "indicadores"],
  adoptante: ["adopcion"], // #85: el adoptante no ve nada del personal
};

/** Pantallas del rol, la primera es la de inicio. Un rol desconocido no ve nada. */
export function pantallasDelRol(rol: string): Pantalla[] {
  return POR_ROL[rol] ?? [];
}
