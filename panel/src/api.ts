// Cliente de la API REST. El token vive solo en memoria (nunca en localStorage): al recargar
// la página hay que iniciar sesión otra vez, a cambio de que un script ajeno no pueda leerlo.

export type Prioridad = "critica" | "alta" | "media" | "baja";

export interface Cuenta { correo: string; nombre: string; rol: string }

export interface ReporteEnCola {
  codigo: string;
  prioridad: Prioridad;
  estado: string;
  confianza: number | null;
  evidencias: string[];
}

export interface RespuestaConfirmacion {
  codigo: string;
  estado: string;
  prioridad: Prioridad;
  ajustada: boolean;
  avisos: { programados: number; estado: "pendiente" | "sin_destinatarios" | "no_aplica" };
}

export class ErrorApi extends Error {
  constructor(public estado: number, public detalle: string) {
    super(detalle);
  }
}

async function pedir<T>(ruta: string, opciones: RequestInit = {}, token?: string): Promise<T> {
  const cabeceras = new Headers(opciones.headers);
  if (token) cabeceras.set("Authorization", `Bearer ${token}`);
  const respuesta = await fetch(ruta, { ...opciones, headers: cabeceras });
  const cuerpo = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    const detalle = typeof cuerpo.detail === "string" ? cuerpo.detail : "Datos no válidos.";
    throw new ErrorApi(respuesta.status, detalle);
  }
  return cuerpo as T;
}

export async function iniciarSesion(correo: string, clave: string): Promise<string> {
  const formulario = new URLSearchParams({ username: correo, password: clave });
  const datos = await pedir<{ access_token: string }>("/auth/token", {
    method: "POST",
    body: formulario,
  });
  return datos.access_token;
}

export const miCuenta = (token: string) => pedir<Cuenta>("/auth/yo", {}, token);
