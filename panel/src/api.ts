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
  descripcion: string; // lo que escribió el ciudadano
  creado_en: string; // UTC (D-06)
  video_segundos: number | null; // null: el reporte no trae video
  // #496: nivel (urgente, alta o normal), más de 72 h sin avanzar y lo que dice el reporte.
  nivel: "urgente" | "alta" | "normal";
  atrasado: boolean;
  especie: string | null;
  estado_animal: string | null;
  ubicacion: { latitud: number | null; longitud: number | null; direccion: string | null;
               comuna: number | null };
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

/** Render gratis se duerme. Si una petición pasa de este tiempo, el panel muestra «El servidor
 *  está despertando» (Despertando.tsx) en vez de parecer colgado. */
export const ESPERA_LENTA_MS = 4000;
type OyenteDeEspera = (peticionesLentas: number) => void;
const oyentes = new Set<OyenteDeEspera>();
let lentas = 0;

/** Avisa cada vez que cambia cuántas peticiones llevan más de ESPERA_LENTA_MS. Devuelve la
 *  función para dejar de oír. */
export function alCambiarEspera(oyente: OyenteDeEspera): () => void {
  oyentes.add(oyente);
  return () => { oyentes.delete(oyente); };
}

function contarLenta(cambio: number): void {
  lentas += cambio;
  oyentes.forEach((oyente) => oyente(lentas));
}

export async function conAvisoDeEspera<T>(promesa: Promise<T>): Promise<T> {
  let avisada = false;
  const reloj = setTimeout(() => { avisada = true; contarLenta(1); }, ESPERA_LENTA_MS);
  try {
    return await promesa;
  } finally {
    clearTimeout(reloj);
    if (avisada) contarLenta(-1);
  }
}

export async function pedir<T>(ruta: string, opciones: RequestInit = {}, token?: string): Promise<T> {
  const cabeceras = new Headers(opciones.headers);
  if (token) cabeceras.set("Authorization", `Bearer ${token}`);
  const respuesta = await conAvisoDeEspera(fetch(ruta, { ...opciones, headers: cabeceras }));
  // Un cuerpo que no es JSON (vacío, o la página HTML de Render) no es lo mismo que un JSON
  // null: «sin rescate activo» responde null y debe llegar tal cual.
  const cuerpo: unknown = await respuesta.json().catch(() => SIN_JSON);
  if (!respuesta.ok) {
    throw new ErrorApi(respuesta.status,
                       mensajeDeError(respuesta.status, cuerpo === SIN_JSON ? null : cuerpo));
  }
  return (cuerpo === SIN_JSON ? {} : cuerpo) as T;
}

const SIN_JSON = Symbol("sin JSON");

/** #396: Render dormido o caído responde 502/503 con una página HTML; un fallo interno, 500.
 *  Nada de eso es culpa de lo que escribió la persona: nunca «Datos no válidos». */
export const MENSAJE_SERVIDOR = "El servidor tuvo un problema, intenta de nuevo en un momento.";

export function mensajeDeError(estado: number, cuerpo: unknown): string {
  if (estado >= 500 || cuerpo === null || typeof cuerpo !== "object") return MENSAJE_SERVIDOR;
  const detalle = (cuerpo as { detail?: unknown }).detail;
  return typeof detalle === "string" ? detalle : "Datos no válidos.";
}

/** #486: la puerta por la que se entra. El servidor responde 403 (sin token) si el rol de la
 *  cuenta no es de esa puerta: el adoptante entra por «Adoptar» y el personal por la suya. */
export type Portal = "adoptante" | "personal";

export async function iniciarSesion(correo: string, clave: string, portal: Portal): Promise<string> {
  const formulario = new URLSearchParams({ username: correo, password: clave, portal });
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
export function descartar(token: string, codigo: string, motivo: "falso" | "duplicado" | "archivado",
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
