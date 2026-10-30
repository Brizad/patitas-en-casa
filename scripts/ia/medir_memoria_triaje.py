"""Mide memoria y tiempo del triaje con el Transformer ONNX (fase 7). Solo Linux (/proc).

Render gratis da 512 MB por proceso; la decisión de despliegue pide dejar ≥ 150 MB libres.
Mide la memoria residente (RSS) del proceso: al arrancar, con la app creada (repositorios en
memoria, como las pruebas), con el modelo ONNX cargado y tras clasificar la prueba fija; y el
pico (VmHWM). Tiempo por predicción con 1 hilo, como en Render.

Uso:  python scripts/ia/medir_memoria_triaje.py --onnx-dir app/triaje/onnx --salida memoria.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))


def memoria_mb(campo: str = "VmRSS") -> float:
    for linea in Path("/proc/self/status").read_text().splitlines():
        if linea.startswith(campo + ":"):
            return round(int(linea.split()[1]) / 1024, 1)
    raise RuntimeError(f"{campo} no está en /proc/self/status")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--onnx-dir", type=Path, required=True)
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    medidas = {"inicio_mb": memoria_mb()}

    from app.api.main import crear_app
    from app.cupos.repositorio import RepositorioCuposEnMemoria
    from app.dominio.modelos import Refugio
    from app.reportes.repositorio import RepositorioEnMemoria
    from app.seguridad.tokens import EmisorTokens
    from app.usuarios.repositorio import RepositorioUsuariosEnMemoria

    crear_app(RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("R", capacidad=40)),
              repositorio_usuarios=RepositorioUsuariosEnMemoria(),
              emisor_tokens=EmisorTokens("x" * 40))
    medidas["app_creada_mb"] = memoria_mb()

    from app.triaje.combinado import clasificador_combinado
    from app.triaje.modelo_onnx import ModeloOnnx
    from scripts.ia.datos_triaje import leer

    modelo = ModeloOnnx.desde_directorio(args.onnx_dir, hilos=1)
    medidas["modelo_cargado_mb"] = memoria_mb()
    clasificar = clasificador_combinado(modelo)
    tiempos = []
    for texto, _, _ in leer(RAIZ / "scripts" / "ia" / "datos" / "triaje_prueba.csv"):
        inicio = time.perf_counter()
        clasificar(texto)
        tiempos.append((time.perf_counter() - inicio) * 1000)
    tiempos.sort()
    medidas.update({
        "tras_1200_predicciones_mb": memoria_mb(), "pico_mb": memoria_mb("VmHWM"),
        "modelo_mb_en_disco": round((args.onnx_dir / "modelo_int8.onnx").stat().st_size / 1e6, 1),
        "ms_mediana": round(statistics.median(tiempos), 1),
        "ms_p95": round(tiempos[int(len(tiempos) * 0.95)], 1), "ms_max": round(tiempos[-1], 1),
    })
    medidas["libres_de_512_mb"] = round(512 - medidas["pico_mb"], 1)
    print(json.dumps(medidas, indent=1))
    if args.salida:
        args.salida.write_text(json.dumps(medidas, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
