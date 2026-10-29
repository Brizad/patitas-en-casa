// Qué pantallas ve cada rol (fase 1, #67). El servidor es quien decide (401/403): esto solo
// evita mostrar botones que siempre fallarían. Función pura: se prueba sin navegador.

export type Pantalla = "cola" | "rescates" | "refugio" | "administracion";

export const NOMBRE_PANTALLA: Record<Pantalla, string> = {
  cola: "Cola de triaje",
  rescates: "Mis rescates",
  refugio: "Refugio",
  administracion: "Administración",
};

const POR_ROL: Record<string, Pantalla[]> = {
  veterinario: ["cola", "refugio"],
  coordinador: ["refugio", "cola"],
  rescatista: ["rescates"],
  administrador: ["administracion"],
};

/** Pantallas del rol, la primera es la de inicio. Un rol desconocido no ve nada. */
export function pantallasDelRol(rol: string): Pantalla[] {
  return POR_ROL[rol] ?? [];
}
