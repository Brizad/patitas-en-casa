// Textos que ve el personal. Funciones puras: se prueban sin navegador (mensajes.test.ts).
import { ErrorApi } from "./api";

export function textoError(error: unknown): string {
  if (!(error instanceof ErrorApi)) return "No hay conexión con el servidor. Intenta de nuevo.";
  switch (error.estado) {
    case 401: return "Correo o contraseña incorrectos.";
    case 403: return "Tu rol no permite esta acción.";
    case 429: return "Demasiados intentos. Espera unos minutos antes de volver a intentar.";
    default: return error.detalle;
  }
}
