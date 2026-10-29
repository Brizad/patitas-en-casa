#!/usr/bin/env bash
# Arranca el trabajador local de video (#125) contra la API de Render.
# Pide el token sin mostrarlo en pantalla y nunca lo imprime. Uso: bash arrancar_nodo.sh
# Para analizar un archivo suelto sin token: bash arrancar_nodo.sh --video ruta/al/video.mp4
set -euo pipefail

CARPETA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PATITAS_PYTHON:-$HOME/pv/bin/python}"
GUARDADO="$HOME/.patitas-video/token"
export PATITAS_API_URL="${PATITAS_API_URL:-https://patitas-en-casa-pnnk.onrender.com}"

if [ ! -x "$PYTHON" ]; then
  echo "No encuentro el entorno de Python ($PYTHON). Corre primero: bash instalar_nodo.sh"
  exit 1
fi

if [ "${1:-}" != "--video" ] && [ -z "${PATITAS_VIDEO_TOKEN:-}" ]; then
  if [ -r "$GUARDADO" ]; then
    PATITAS_VIDEO_TOKEN="$(cat "$GUARDADO")"
  else
    echo "Pega el token de Render (PATITAS_VIDEO_TOKEN) y pulsa Enter."
    echo "No se verá mientras lo pegas; es normal."
    read -rs PATITAS_VIDEO_TOKEN
    PATITAS_VIDEO_TOKEN="${PATITAS_VIDEO_TOKEN%$'\r'}"  # quita el fin de línea de Windows
    echo
    if [ -z "$PATITAS_VIDEO_TOKEN" ]; then
      echo "No se recibió ningún token."
      exit 1
    fi
    read -rp "¿Guardarlo en este equipo para no pedirlo otra vez? (s/N) " guardar
    guardar="${guardar%$'\r'}"
    if [ "$guardar" = "s" ] || [ "$guardar" = "S" ]; then
      mkdir -p "$(dirname "$GUARDADO")"
      (umask 077 && printf '%s' "$PATITAS_VIDEO_TOKEN" > "$GUARDADO")
      echo "Guardado en $GUARDADO (solo tu usuario puede leerlo; bórralo para olvidarlo)."
    fi
  fi
fi
export PATITAS_VIDEO_TOKEN="${PATITAS_VIDEO_TOKEN:-}"

echo "Trabajando contra $PATITAS_API_URL. Deja esta ventana abierta; Ctrl+C para detener."
cd "$CARPETA"
exec "$PYTHON" -m patitas_video.trabajador "$@"
