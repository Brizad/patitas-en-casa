// Qué pantallas ve cada rol (fase 1, #67). El servidor es quien decide (401/403): esto solo
// evita mostrar botones que siempre fallarían. Función pura: se prueba sin navegador.

export type Pantalla = "cola" | "historial" | "rescates" | "mis_rescates" | "refugio" | "administracion" | "piloto" | "adopcion"
  | "adopciones" | "indicadores" | "informes";

export const NOMBRE_PANTALLA: Record<Pantalla, string> = {
  cola: "Cola de triaje",
  historial: "Historial",
  rescates: "Ofertas y rescate actual",
  mis_rescates: "Mis rescates",
  refugio: "Refugio",
  administracion: "Administración",
  piloto: "Modo piloto",
  adopcion: "Adopción",
  adopciones: "Adopciones",
  indicadores: "Indicadores",
  informes: "Informes de rescate", // #504
};

const POR_ROL: Record<string, Pantalla[]> = {
  veterinario: ["cola", "historial", "informes", "refugio"],
  coordinador: ["refugio", "adopciones", "cola", "informes", "indicadores"],
  rescatista: ["rescates", "mis_rescates"],
  administrador: ["administracion", "piloto", "indicadores"],  // #258: piloto RNF-06
  adoptante: ["adopcion"], // #85: el adoptante no ve nada del personal
  alcaldia: ["indicadores"], // #108 (RF-13): solo indicadores anonimizados
};

/** Pantallas del rol, la primera es la de inicio. Un rol desconocido no ve nada. */
export function pantallasDelRol(rol: string): Pantalla[] {
  return POR_ROL[rol] ?? [];
}
