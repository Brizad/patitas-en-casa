"""Clasificador entrenado (TF-IDF + regresión logística) en Python puro (fase 4, #95).

El modelo lo entrena scripts/ia/entrenar_triaje.py y lo guarda en modelo_tfidf_v1.json. Aquí
se repite el cálculo de scikit-learn sin cargar scikit-learn (cabe en 512 MB):

1. Normalizar el texto y partirlo en palabras de 2 o más letras (mismo patrón de sklearn).
2. Contar palabras y pares de palabras que estén en el vocabulario.
3. Peso TF-IDF = conteo × idf; luego se divide por la longitud del vector (norma L2).
4. Puntaje por clase = Σ peso × coeficiente + intercepto; softmax → probabilidades.
5. Si P(crítica) ≥ umbral (ajustado para recall alto, RNF-03) → crítica; si no, la más alta.

Las evidencias (RNF-09) son los términos que más empujaron hacia la prioridad elegida.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import cache
from pathlib import Path

from app.dominio.modelos import Prioridad
from app.triaje.clasificador import Resultado
from app.triaje.normalizacion import normalizar

ARCHIVO = Path(__file__).with_name("modelo_tfidf_v1.json")
PATRON_PALABRA = re.compile(r"(?u)\b\w\w+\b")  # token_pattern por defecto de scikit-learn
MIN_EVIDENCIAS = 3


class ModeloTriaje:
    def __init__(self, datos: dict) -> None:
        self.version: str = datos["version"]
        self._clases = [Prioridad(c) for c in datos["clases"]]
        self._indice = {t: i for i, t in enumerate(datos["terminos"])}
        self._terminos = datos["terminos"]
        self._idf = datos["idf"]
        self._coef = datos["coeficientes"]
        self._intercepto = datos["intercepto"]
        self._umbral_critica = datos["umbral_critica"]

    def vector(self, texto: str) -> dict[int, float]:
        palabras = PATRON_PALABRA.findall(normalizar(texto))
        terminos = palabras + [f"{a} {b}" for a, b in zip(palabras, palabras[1:], strict=False)]
        conteo = Counter(t for t in terminos if t in self._indice)
        pesos = {self._indice[t]: n * self._idf[self._indice[t]] for t, n in conteo.items()}
        norma = math.sqrt(sum(p * p for p in pesos.values())) or 1.0
        return {i: p / norma for i, p in pesos.items()}

    def probabilidades(self, texto: str) -> dict[Prioridad, float]:
        x = self.vector(texto)
        puntajes = [sum(p * fila[i] for i, p in x.items()) + b
                    for fila, b in zip(self._coef, self._intercepto, strict=True)]
        maximo = max(puntajes)
        exps = [math.exp(s - maximo) for s in puntajes]
        total = sum(exps)
        return {c: e / total for c, e in zip(self._clases, exps, strict=True)}

    def clasificar(self, texto: str) -> Resultado:
        probs = self.probabilidades(texto)
        if probs[Prioridad.CRITICA] >= self._umbral_critica:
            elegida = Prioridad.CRITICA
        else:
            elegida = max(probs, key=probs.get)
        return Resultado(elegida, round(probs[elegida], 2), self._evidencias(texto, elegida))

    def _evidencias(self, texto: str, clase: Prioridad) -> list[str]:
        fila = self._coef[self._clases.index(clase)]
        aportes = sorted(((p * fila[i], i) for i, p in self.vector(texto).items()),
                         reverse=True)
        return [f"«{self._terminos[i]}» apunta a {clase.value}"
                for aporte, i in aportes[:MIN_EVIDENCIAS] if aporte > 0]


@cache
def cargar_modelo(archivo: Path = ARCHIVO) -> ModeloTriaje:
    return ModeloTriaje(json.loads(archivo.read_text(encoding="utf-8")))
