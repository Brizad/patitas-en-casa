#!/usr/bin/env bash
# Instala el trabajador local de video (#125) en Ubuntu o WSL2. Se puede correr otra vez
# para actualizarlo: no borra nada. Uso: bash instalar_nodo.sh
set -euo pipefail

REPO_URL="https://github.com/Brizad/patitas-en-casa.git"
CARPETA="${PATITAS_CARPETA:-$HOME/patitas}"
ENTORNO="${PATITAS_ENTORNO:-$HOME/pv}"
TORCH="torch==2.14.1 torchvision==0.29.2"

paso() { printf '\n==> %s\n' "$1"; }

if [ "$(uname -s)" != "Linux" ]; then
  echo "Este instalador es para Ubuntu o WSL2. En Windows abre primero la app «Ubuntu»."
  exit 1
fi

paso "1/5 Programas del sistema (te pedirá la contraseña de Ubuntu)"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git libegl1 libgles2

paso "2/5 Código de Patitas en Casa en $CARPETA"
if [ -d "$CARPETA/.git" ]; then
  git -C "$CARPETA" pull --ff-only
else
  git clone --depth 1 "$REPO_URL" "$CARPETA"
fi

paso "3/5 Entorno de Python en $ENTORNO"
[ -x "$ENTORNO/bin/python" ] || python3 -m venv "$ENTORNO"
"$ENTORNO/bin/python" -m pip install --upgrade pip

paso "4/5 Librerías de IA (unos 3 GB; la primera vez tarda)"
# shellcheck disable=SC2086  # TORCH son dos paquetes a propósito
"$ENTORNO/bin/pip" install $TORCH --index-url https://download.pytorch.org/whl/cpu
"$ENTORNO/bin/pip" install -r "$CARPETA/servicios/video/requirements.txt"

paso "5/5 Comprobación"
cd "$CARPETA/servicios/video"
"$ENTORNO/bin/python" -c "import cv2, mediapipe, deeplabcut, patitas_video.adaptadores" \
  && echo "Listo. Para arrancar: bash $CARPETA/servicios/video/arrancar_nodo.sh"
