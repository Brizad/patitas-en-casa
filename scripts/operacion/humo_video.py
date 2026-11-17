"""Prueba de humo del video de punta a punta (#231) contra una API que ya está corriendo.

Hace lo mismo que pasa en producción, con el nodo real (MediaPipe + DeepLabCut + ffmpeg):

    ciudadano crea el reporte → sube el video → el nodo lo reclama, lo analiza, sube la vista
    previa y entrega el resultado → el veterinario ve el estado y descarga la vista.

Falla (salida 1) si la vista previa no llega hasta `GET /reportes/{codigo}/video/vista.mp4`, y
dice el motivo que mandó el nodo. La usa `.github/workflows/video-humo.yml`; en tu PC:

    python scripts/operacion/humo_video.py --api http://127.0.0.1:8000 --video perro.mp4 \
        --correo veterinaria@demo.patitas.co

Lee del entorno PATITAS_VIDEO_TOKEN (el del nodo) y HUMO_CONTRASENA (la de esa cuenta). No
imprime ninguno de los dos.
"""
from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[2]
DESCRIPCION = "Prueba de humo del video: perro que cojea cerca del parque principal."
MAX_VISTA = 5 * 1024 * 1024


class HumoFallido(AssertionError):
    pass


def exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise HumoFallido(mensaje)


def correr_nodo(api: str) -> None:
    """Un ciclo del trabajador real, como lo arranca arrancar_nodo.sh."""
    entorno = {**os.environ, "PATITAS_API_URL": api}
    subprocess.run([sys.executable, "-m", "patitas_video.trabajador", "--una-vez"],
                   cwd=RAIZ / "servicios" / "video", env=entorno, check=True, timeout=1500)


def humo(http: httpx.Client, video: bytes, correo: str, contrasena: str,
         nodo: Callable[[], None], decir: Callable[[str], None] = print) -> dict:
    """Devuelve el análisis que ve el veterinario. `nodo()` procesa un trabajo."""
    llave = secrets.token_hex(16)
    r = http.post("/reportes", json={"descripcion": DESCRIPCION, "direccion": "Calle 10 # 5-20"},
                  headers={"Idempotency-Key": llave})
    exigir(r.status_code == 201, f"crear el reporte respondió {r.status_code}: {r.text[:200]}")
    codigo = r.json()["codigo"]
    r = http.post(f"/reportes/{codigo}/video", content=video,
                  headers={"Idempotency-Key": llave, "Content-Type": "video/mp4"})
    exigir(r.status_code == 202, f"subir el video respondió {r.status_code}: {r.text[:200]}")
    decir(f"1/4 reporte {codigo} creado y video subido ({len(video) // 1024} KB)")

    nodo()
    decir("2/4 el nodo procesó un trabajo")

    r = http.post("/auth/token", data={"username": correo, "password": contrasena})
    exigir(r.status_code == 200, f"el inicio de sesión respondió {r.status_code}")
    sesion = {"Authorization": f"Bearer {r.json()['access_token']}"}
    analisis = http.get(f"/reportes/{codigo}/video", headers=sesion).json()
    medidas = analisis.get("medidas", {})
    exigir(analisis.get("estado") in ("terminado", "no_concluyente"),
           f"el análisis quedó «{analisis.get('estado')}»: {analisis.get('motivo')}")
    exigir(analisis.get("tiene_vista") is True,
           f"el análisis llegó SIN vista previa: {medidas.get('sin_vista', 'el nodo no dijo')}")
    decir(f"3/4 análisis «{analisis['estado']}» con vista (nodo {medidas.get('version_nodo')})")

    r = http.get(f"/reportes/{codigo}/video/vista.mp4", headers=sesion)
    exigir(r.status_code == 200, f"descargar la vista respondió {r.status_code}")
    exigir(r.headers.get("content-type") == "video/mp4", "la vista no llega como video/mp4")
    exigir(r.content[4:8] == b"ftyp", "la vista no es un MP4")
    exigir(len(r.content) <= MAX_VISTA, f"la vista pesa {len(r.content)} bytes (más de 5 MB)")
    estado_nodo = http.get("/video/nodo", headers=sesion).json()
    exigir(estado_nodo.get("al_dia") is True,
           f"la API ve un nodo viejo: {estado_nodo.get('version')}")
    decir(f"4/4 el veterinario descarga la vista ({len(r.content) // 1024} KB) y el nodo está "
          "al día")
    return analisis


def main() -> int:
    opciones = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    opciones.add_argument("--api", required=True)
    opciones.add_argument("--video", required=True, type=Path)
    opciones.add_argument("--correo", required=True)
    o = opciones.parse_args()
    contrasena = os.environ.get("HUMO_CONTRASENA", "")
    if not contrasena or not os.environ.get("PATITAS_VIDEO_TOKEN"):
        print("Faltan HUMO_CONTRASENA o PATITAS_VIDEO_TOKEN en el entorno.")
        return 2
    try:
        with httpx.Client(base_url=o.api, timeout=120) as http:
            humo(http, o.video.read_bytes(), o.correo, contrasena, lambda: correr_nodo(o.api))
    except HumoFallido as fallo:
        print(f"HUMO FALLIDO: {fallo}")
        return 1
    print("Humo del video: todo bien.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
