"""Diagnóstico de un video (#125): ¿se ve el animal? ¿qué tan seguros están los puntos?

Sirve para ajustar los umbrales de `marcha.py` con datos y no a ojo:

    python -m patitas_video.diagnostico perro.mp4
"""
from __future__ import annotations

import statistics
import sys

from patitas_video.adaptadores import DetectorMediaPipe, EstimadorDeepLabCut, LectorOpenCV
from patitas_video.analisis import ESPECIES, FPS
from patitas_video.marcha import PATAS

PRINCIPALES = ("neck_base", "back_middle", "tail_base", *PATAS)


def resumen(valores: list[float]) -> str:
    if not valores:
        return "sin datos"
    cuartiles = statistics.quantiles(valores, n=4) if len(valores) > 1 else valores * 3
    return f"p25 {cuartiles[0]:.2f} · mediana {statistics.median(valores):.2f}"


def main() -> None:
    lector, detector, estimador = LectorOpenCV(), DetectorMediaPipe(), EstimadorDeepLabCut()
    total, puntajes, confianzas = 0, [], {}
    for imagen in lector.cuadros(sys.argv[1], FPS):
        total += 1
        caja = detector.detectar(imagen)
        if caja is None or caja.especie not in ESPECIES:
            continue
        puntajes.append(caja.puntaje)
        for nombre, (_x, _y, confianza) in estimador.puntos(imagen, caja).items():
            confianzas.setdefault(nombre, []).append(confianza)
    print(f"cuadros: {total} · con perro o gato: {len(puntajes)} · detector: {resumen(puntajes)}")
    for nombre in PRINCIPALES:
        print(f"  {nombre:16} {resumen(confianzas.get(nombre, []))}")
    otros = sorted(set(confianzas) - set(PRINCIPALES))
    medianas = (f"{n} {statistics.median(confianzas[n]):.2f}" for n in otros)
    print("  otros puntos:", ", ".join(medianas))
    detector.cerrar()


if __name__ == "__main__":
    main()
