"""Prioridad a partir de las medidas de la marcha (#125, RF-03, RNF-09).

Una red neuronal pequeña (MLP: 5 entradas, 8 neuronas ocultas, 4 salidas) entrenada con
scikit-learn y exportada a JSON; aquí se ejecuta con Python puro. Se entrenó con medidas
SINTÉTICAS (`entrenamiento/entrenar.py`): no hay todavía videos etiquetados por veterinarios
(DT-04). Por eso dos reglas de seguridad mandan sobre el modelo: si el animal no se pone de
pie o no apoya una pata, la prioridad nunca queda por debajo de «alta».
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from patitas_video import marcha
from patitas_video.marcha import Medidas

MODELO = Path(__file__).with_name("modelo_marcha_v1.json")
ORDEN = ("critica", "alta", "media", "baja")  # de más grave a menos grave


@dataclass
class Resultado:
    prioridad: str
    confianza: float
    evidencias: list[str] = field(default_factory=list)


def entradas(m: Medidas) -> list[float]:
    """Cinco números entre 0 y 1; más alto = más preocupante. El orden es el del JSON."""
    regularidad = 1.0 if m.regularidad is None else m.regularidad
    return [1 - m.de_pie, m.asimetria, m.fraccion_sin_apoyo, 1 - regularidad,
            1 - min(1.0, m.desplazamiento / 0.5)]


def _pct(valor: float) -> str:
    return f"{round(valor * 100)} %"


def evidencias(m: Medidas) -> list[str]:
    """Al menos 3 frases que un veterinario puede comprobar mirando el video (RNF-09)."""
    frases = [f"se mantiene de pie en el {_pct(m.de_pie)} de los cuadros"
              if m.de_pie >= 0.2 else "no se pone de pie en el video"]
    if m.pata_sin_apoyo:
        frases.append(f"no apoya la pata {m.pata_sin_apoyo} "
                      f"({_pct(m.fraccion_sin_apoyo)} de los cuadros en el aire)")
    else:
        frases.append("apoya las cuatro patas")
    frases.append(f"cojea: una pata se mueve {_pct(m.asimetria)} distinto de su par"
                  if m.asimetria >= marcha.UMBRAL_COJERA
                  else "mueve las patas de forma pareja")
    if m.desplazamiento < marcha.UMBRAL_INMOVIL:
        frases.append("casi no se desplaza")
    elif m.regularidad is not None and m.regularidad < marcha.UMBRAL_IRREGULAR:
        frases.append("el paso es irregular")
    return frases


class ClasificadorMarcha:
    def __init__(self, datos: dict):
        self.version: str = datos["version"]
        self.origen_de_los_datos: str = datos["datos"]
        self._clases: list[str] = datos["clases"]
        self._media, self._escala = datos["media"], datos["escala"]
        self._capas = datos["capas"]

    @classmethod
    def desde_json(cls, ruta: Path = MODELO) -> ClasificadorMarcha:
        return cls(json.loads(ruta.read_text(encoding="utf-8")))

    def probabilidades(self, x: list[float]) -> dict[str, float]:
        valores = [(v - m) / e for v, m, e in zip(x, self._media, self._escala, strict=True)]
        for i, capa in enumerate(self._capas):
            valores = [sum(v * fila[j] for v, fila in zip(valores, capa["pesos"], strict=True))
                       + b for j, b in enumerate(capa["sesgos"])]
            if i < len(self._capas) - 1:
                valores = [max(0.0, v) for v in valores]  # ReLU en las capas ocultas
        mayor = max(valores)
        exps = [math.exp(v - mayor) for v in valores]
        return {c: e / sum(exps) for c, e in zip(self._clases, exps, strict=True)}

    def clasificar(self, m: Medidas) -> Resultado:
        probs = self.probabilidades(entradas(m))
        prioridad = max(probs, key=probs.get)
        resultado = Resultado(prioridad, round(probs[prioridad], 3), evidencias(m))
        grave = m.de_pie < 0.2 or m.pata_sin_apoyo is not None
        if grave and ORDEN.index(prioridad) > ORDEN.index("alta"):
            resultado.prioridad = "alta"
            resultado.evidencias.append(
                f"regla de seguridad: el modelo sugería {prioridad}; sin apoyo o sin ponerse "
                "de pie nunca queda por debajo de alta")
        return resultado
