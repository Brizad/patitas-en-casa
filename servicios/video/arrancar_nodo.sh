#!/usr/bin/env bash
# Arranca el trabajador local de video (#125) contra la API de Render.
# Pide el token sin mostrarlo en pantalla y nunca lo imprime. Uso: bash arrancar_nodo.sh
# Para analizar un archivo suelto sin token: bash arrancar_nodo.sh --video ruta/al/video.mp4
#
# #231: antes de trabajar se pone al día con «main» (solo en la carpeta que dejó
# instalar_nodo.sh; nunca en tu copia de desarrollo) y avisa si falta ffmpeg. Para arrancar sin
# actualizar: PATITAS_SIN_ACTUALIZAR=1 bash arrancar_nodo.sh
set -euo pipefail

CARPETA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$CARPETA/../.." && pwd)"
PYTHON="${PATITAS_PYTHON:-$HOME/pv/bin/python}"
GUARDADO="$HOME/.patitas-video/token"
MARCA="$HOME/.patitas-video/carpeta"   # la escribe instalar_nodo.sh: dónde vive el nodo
FFMPEG="${PATITAS_FFMPEG:-ffmpeg}"
export PATITAS_API_URL="${PATITAS_API_URL:-https://patitas-en-casa-pnnk.onrender.com}"

# Devuelve 0 si el código cambió (hay que volver a leer este script).
actualizar() {
  [ -z "${PATITAS_SIN_ACTUALIZAR:-}" ] || return 1
  if [ ! -r "$MARCA" ] || [ "$(cat "$MARCA")" != "$RAIZ" ] || [ ! -d "$RAIZ/.git" ]; then
    echo "Este nodo no se actualiza solo. Para activarlo, corre una vez: bash $CARPETA/instalar_nodo.sh"
    return 1
  fi
  if ! git -C "$RAIZ" fetch --quiet --depth 1 origin main 2>/dev/null; then
    echo "Sin conexión con GitHub: sigo con el código que ya tengo."
    return 1
  fi
  local antes nuevo
  antes="$(git -C "$RAIZ" rev-parse HEAD)"
  nuevo="$(git -C "$RAIZ" rev-parse FETCH_HEAD)"
  [ "$antes" != "$nuevo" ] || return 1
  if [ -n "$(git -C "$RAIZ" status --porcelain)" ]; then
    # Nada se pierde: lo cambiado a mano queda guardado y se recupera con «git stash pop».
    git -C "$RAIZ" -c user.name=nodo -c user.email=nodo@localhost stash push \
      --include-untracked --quiet -m "antes de actualizar el nodo"
    echo "Había archivos cambiados a mano en $RAIZ; quedaron guardados (git -C $RAIZ stash list)."
  fi
  git -C "$RAIZ" reset --quiet --hard "$nuevo"
  echo "Nodo actualizado a $(git -C "$RAIZ" rev-parse --short HEAD)."
  if ! git -C "$RAIZ" diff --quiet "$antes" "$nuevo" -- servicios/video/requirements.txt; then
    echo "Cambiaron las librerías: instalando (puede tardar)..."
    "$PYTHON" -m pip install -r "$CARPETA/requirements.txt"
  fi
  return 0
}

pedir_token() {
  if [ -r "$GUARDADO" ]; then
    PATITAS_VIDEO_TOKEN="$(cat "$GUARDADO")"
    return
  fi
  echo "Pega el token de Render (PATITAS_VIDEO_TOKEN) y pulsa Enter."
  echo "No se verá mientras lo pegas; es normal."
  read -rs PATITAS_VIDEO_TOKEN
  PATITAS_VIDEO_TOKEN="${PATITAS_VIDEO_TOKEN%$'\r'}"  # quita el fin de línea de Windows
  echo
  if [ -z "$PATITAS_VIDEO_TOKEN" ]; then
    echo "No se recibió ningún token."
    exit 1
  fi
  local guardar
  read -rp "¿Guardarlo en este equipo para no pedirlo otra vez? (s/N) " guardar
  guardar="${guardar%$'\r'}"
  if [ "$guardar" = "s" ] || [ "$guardar" = "S" ]; then
    mkdir -p "$(dirname "$GUARDADO")"
    (umask 077 && printf '%s' "$PATITAS_VIDEO_TOKEN" > "$GUARDADO")
    echo "Guardado en $GUARDADO (solo tu usuario puede leerlo; bórralo para olvidarlo)."
  fi
}

# Todo dentro de una función: bash lee el archivo entero antes de ejecutar, así que
# actualizarlo mientras corre no lo rompe.
principal() {
  if [ ! -x "$PYTHON" ]; then
    echo "No encuentro el entorno de Python ($PYTHON). Corre primero: bash instalar_nodo.sh"
    exit 1
  fi
  if [ -z "${PATITAS_YA_ACTUALIZADO:-}" ] && actualizar; then
    PATITAS_YA_ACTUALIZADO=1 exec bash "$CARPETA/arrancar_nodo.sh" "$@"  # el script nuevo
  fi
  if ! command -v "$FFMPEG" > /dev/null 2>&1; then
    echo "AVISO: falta ffmpeg. Los análisis llegarán SIN vista previa para el veterinario."
    echo "       Instálalo y vuelve a arrancar: sudo apt install -y ffmpeg"
  fi
  if [ "${1:-}" != "--video" ] && [ -z "${PATITAS_VIDEO_TOKEN:-}" ]; then
    pedir_token
  fi
  export PATITAS_VIDEO_TOKEN="${PATITAS_VIDEO_TOKEN:-}"

  echo "Trabajando contra $PATITAS_API_URL. Deja esta ventana abierta; Ctrl+C para detener."
  cd "$CARPETA"
  exec "$PYTHON" -m patitas_video.trabajador "$@"
}

principal "$@"
