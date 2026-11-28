// Fotos de evidencia (#504). Antes de subir, el navegador las reduce a 1280 px como máximo y las
// vuelve a codificar como JPEG de ~200 KB con un canvas. Así pesan poco y, como el canvas solo
// copia los píxeles, se pierden los metadatos EXIF (incluido el GPS del teléfono).
import { ErrorApi, conAvisoDeEspera, mensajeDeError } from "./api";

export const LADO_MAXIMO = 1280;
export const PESO_OBJETIVO = 200 * 1024;
export const MAX_FOTOS = 3;

/** Tamaño final conservando la proporción, sin agrandar nunca. */
export function medidaReducida(ancho: number, alto: number, maximo = LADO_MAXIMO): [number, number] {
  const escala = Math.min(1, maximo / Math.max(ancho, alto));
  return [Math.max(1, Math.round(ancho * escala)), Math.max(1, Math.round(alto * escala))];
}

function aBlob(lienzo: HTMLCanvasElement, calidad: number): Promise<Blob> {
  return new Promise((listo, falla) => lienzo.toBlob(
    (b) => (b ? listo(b) : falla(new Error("No se pudo preparar la foto."))), "image/jpeg", calidad));
}

/** Reduce, quita el EXIF y comprime (baja la calidad hasta acercarse a ~200 KB). */
export async function prepararFoto(archivo: Blob): Promise<Blob> {
  // «from-image» respeta la orientación del teléfono antes de que se pierda el EXIF.
  const imagen = await createImageBitmap(archivo, { imageOrientation: "from-image" });
  const [ancho, alto] = medidaReducida(imagen.width, imagen.height);
  const lienzo = document.createElement("canvas");
  lienzo.width = ancho;
  lienzo.height = alto;
  lienzo.getContext("2d")!.drawImage(imagen, 0, 0, ancho, alto);
  imagen.close();
  let blob = await aBlob(lienzo, 0.82);
  for (const calidad of [0.7, 0.6, 0.5]) {
    if (blob.size <= PESO_OBJETIVO) break;
    blob = await aBlob(lienzo, calidad);
  }
  return blob;
}

/** Las fotos de evidencia nunca tienen URL pública: se piden con la sesión y se muestran como
 *  blob local (la CSP admite blob: solo para imágenes del propio navegador). */
export async function fotoConSesion(token: string, url: string): Promise<string> {
  const respuesta = await conAvisoDeEspera(fetch(url, { headers: { Authorization: `Bearer ${token}` } }));
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, mensajeDeError(respuesta.status, null));
  return URL.createObjectURL(await respuesta.blob());
}
