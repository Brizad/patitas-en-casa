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
  version_modelo: string | null; // RF-20
  posibles_duplicados: string[]; // RF-17: a menos de 200 m y 2 horas
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

export async function pedir<T>(ruta: string, opciones: RequestInit = {}, token?: string): Promise<T> {
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

export const cola = (token: string) => pedir<ReporteEnCola[]>("/cola", {}, token);

export function confirmar(token: string, codigo: string, prioridad?: Prioridad,
                          justificacion?: string) {
  return pedir<RespuestaConfirmacion>(`/reportes/${codigo}/confirmacion`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prioridad: prioridad ?? null, justificacion: justificacion ?? null }),
  }, token);
}

/** D-02: falso o duplicado (con el original, opcional). 409 si ya se decidió. */
export function descartar(token: string, codigo: string, motivo: "falso" | "duplicado",
                          justificacion: string, duplicado_de?: string) {
  return pedir(`/reportes/${codigo}/descarte`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ motivo, justificacion, duplicado_de: duplicado_de ?? null }),
  }, token);
}

export interface Aviso { estado: string; intentos: number; ultimo_error: string | null }
export interface ResumenAvisos { resumen: Record<string, number>; avisos: Aviso[] }

export const estadoAvisos = (token: string, codigo: string) =>
  pedir<ResumenAvisos>(`/reportes/${codigo}/avisos`, {}, token);
