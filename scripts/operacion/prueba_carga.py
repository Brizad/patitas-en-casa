"""Prueba de carga para RNF-01 y RNF-14 (#119).

RNF-01: prioridad sugerida en 3 s o menos (percentil 95) con 30 reportes concurrentes,
medido sobre 500 reportes. RNF-14: 200 reportes por hora y 50 usuarios concurrentes del panel.

Qué hace: envía N reportes con C hilos a la vez (cada respuesta ya trae la prioridad
sugerida: el triaje corre dentro de POST /reportes) y, en paralelo, U «usuarios del panel»
que piden la cola una y otra vez. Mide la latencia de cada petición y da el percentil 95.

Uso (contra un servidor LOCAL con la base de pruebas; no contra Render, para no llenar la
base real de reportes falsos):
    python scripts/operacion/prueba_carga.py --url http://127.0.0.1:8001 --token <token>
"""
from __future__ import annotations

import argparse
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

TEXTOS = ["Perro atropellado en la avenida, no se mueve y sangra mucho",
          "Gato con una herida abierta en el lomo debajo de un carro",
          "Perrito que cojea un poco y no come hace dos días",
          "Perra con sarna y garrapatas que duerme en el parque"]


def percentil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int(round(p / 100 * len(ordenados))) - 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8001")
    parser.add_argument("--reportes", type=int, default=500)
    parser.add_argument("--concurrentes", type=int, default=30)
    parser.add_argument("--usuarios-panel", type=int, default=50)
    parser.add_argument("--token", help="token de un veterinario para pedir la cola")
    args = parser.parse_args()

    tiempos_reporte: list[float] = []
    tiempos_cola: list[float] = []
    errores = []
    fin = threading.Event()

    def reportar(i: int) -> None:
        cuerpo = {"descripcion": TEXTOS[i % len(TEXTOS)], "direccion": f"Calle {i}",
                  "comuna": i % 10 + 1}
        inicio = time.perf_counter()
        r = httpx.post(f"{args.url}/reportes", json=cuerpo, timeout=30)
        tiempos_reporte.append(time.perf_counter() - inicio)
        if r.status_code != 201 or "codigo" not in r.json():
            errores.append(r.status_code)

    def usuario_panel() -> None:
        cabeceras = {"Authorization": f"Bearer {args.token}"}
        while not fin.is_set():
            inicio = time.perf_counter()
            r = httpx.get(f"{args.url}/cola", headers=cabeceras, timeout=30)
            tiempos_cola.append(time.perf_counter() - inicio)
            if r.status_code != 200:
                errores.append(r.status_code)
            time.sleep(1)  # una persona no recarga sin parar

    panel = ThreadPoolExecutor(max_workers=args.usuarios_panel)
    if args.token:
        for _ in range(args.usuarios_panel):
            panel.submit(usuario_panel)
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrentes) as hilos:
        list(hilos.map(reportar, range(args.reportes)))
    duracion = time.perf_counter() - inicio
    fin.set()
    panel.shutdown(wait=True)

    print(f"Reportes: {len(tiempos_reporte)} en {duracion:.1f} s con {args.concurrentes} a la vez "
          f"= {len(tiempos_reporte) / duracion * 3600:.0f} reportes/hora")
    print(f"  latencia p50 {statistics.median(tiempos_reporte):.3f} s · "
          f"p95 {percentil(tiempos_reporte, 95):.3f} s · máx {max(tiempos_reporte):.3f} s")
    if tiempos_cola:
        print(f"Panel: {len(tiempos_cola)} consultas de la cola con {args.usuarios_panel} "
              f"usuarios · p95 {percentil(tiempos_cola, 95):.3f} s")
    print(f"Errores: {len(errores)} {sorted(set(errores))}")


if __name__ == "__main__":
    main()
