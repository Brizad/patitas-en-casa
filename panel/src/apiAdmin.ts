// Llamadas del administrador (RF-13, RF-14, RF-16). El servidor exige el rol (403 si no).
import { pedir } from "./api";

export interface CuentaAdmin {
  correo: string; nombre: string; rol: string; activo: boolean; refugio_id: number | null;
}
export interface RefugioAdmin { id: number; nombre: string; capacidad: number; ocupados: number }
export interface CuentaNueva { correo: string; nombre: string; rol: string; contrasena: string }

export const ROLES = ["veterinario", "coordinador", "rescatista", "administrador"];

const enviar = (method: string, cuerpo: unknown): RequestInit => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
});

export const cuentas = (t: string) => pedir<CuentaAdmin[]>("/admin/usuarios", {}, t);
export const crearCuenta = (t: string, c: CuentaNueva) =>
  pedir<CuentaAdmin>("/admin/usuarios", enviar("POST", c), t);
export const cambiarActivo = (t: string, correo: string, activo: boolean) =>
  pedir(`/admin/usuarios/${encodeURIComponent(correo)}/activo`, enviar("PUT", { activo }), t);
export const vincular = (t: string, correo: string, refugio_id: number | null) =>
  pedir(`/admin/usuarios/${encodeURIComponent(correo)}/refugio`,
        enviar("PUT", { refugio_id }), t);
export const refugios = (t: string) => pedir<RefugioAdmin[]>("/admin/refugios", {}, t);
export const crearRefugio = (t: string, nombre: string, capacidad: number) =>
  pedir<RefugioAdmin>("/admin/refugios", enviar("POST", { nombre, capacidad }), t);

/** Política de contraseñas igual a la del servidor (12 a 128): avisa antes de enviar. */
export function problemaContrasena(clave: string): string | null {
  if (clave.length < 12) return "La contraseña debe tener 12 caracteres o más.";
  if (clave.length > 128) return "La contraseña debe tener 128 caracteres o menos.";
  return null;
}
