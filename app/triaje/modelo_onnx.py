"""Triaje con un Transformer afinado y exportado a ONNX int8 (fase 7).

El modelo se afina en GitHub Actions (.github/workflows/entrenar-triaje.yml); aquí solo se usa:
onnxruntime ejecuta la red y tokenizers parte el texto en piezas. Ni torch ni transformers
entran a la API. Tiene la misma forma que el TF-IDF (`version`, `clasificar(texto)`), así que
`combinado.py` lo trata igual: el modelo solo puede SUBIR la prioridad de las reglas.

Pasos de una predicción:
1. Normalizar el texto (minúsculas, sin tildes), igual que al entrenar.
2. Tokenizar: el texto pasa a números de piezas de palabra ([CLS] ... [SEP], máx. N piezas).
3. La red devuelve un puntaje (logit) por clase; softmax → probabilidades.
4. Si P(crítica) ≥ umbral (ajustado en validación para recall alto, RNF-03) → crítica.
"""
from __future__ import annotations

import json
import math
from functools import cache
from pathlib import Path
from typing import Any

from app.dominio.modelos import Prioridad
from app.triaje.clasificador import Resultado
from app.triaje.normalizacion import normalizar

DIRECTORIO = Path(__file__).with_name("onnx")
METADATOS = "triaje_onnx.json"


class ModeloOnnx:
    """`sesion` es una onnxruntime.InferenceSession y `tokenizador` un tokenizers.Tokenizer;
    las pruebas pueden pasar dobles con la misma forma."""

    def __init__(self, metadatos: dict, sesion: Any, tokenizador: Any) -> None:
        self.version: str = metadatos["version"]
        self._clases = [Prioridad(c) for c in metadatos["clases"]]
        self._umbral_critica: float = metadatos["umbral_critica"]
        self._sesion = sesion
        self._entradas = {e.name for e in sesion.get_inputs()}
        self._tokenizador = tokenizador
        self._tokenizador.enable_truncation(max_length=metadatos["max_tokens"])
        self._tokenizador.no_padding()  # un reporte por vez: sin relleno

    @classmethod
    def desde_directorio(cls, directorio: Path = DIRECTORIO, hilos: int = 1) -> ModeloOnnx:
        metadatos = json.loads((directorio / METADATOS).read_text(encoding="utf-8"))
        import onnxruntime  # solo aquí: sin el paquete, la API sigue con el TF-IDF
        from tokenizers import Tokenizer

        opciones = onnxruntime.SessionOptions()
        opciones.intra_op_num_threads = hilos  # Render gratis: 0,1 CPU; más hilos no ayudan
        opciones.inter_op_num_threads = 1
        opciones.enable_cpu_mem_arena = False  # menos memoria reservada de más (512 MB)
        sesion = onnxruntime.InferenceSession(str(directorio / metadatos["archivo"]), opciones,
                                              providers=["CPUExecutionProvider"])
        tokenizador = Tokenizer.from_file(str(directorio / metadatos["tokenizador"]))
        return cls(metadatos, sesion, tokenizador)

    def probabilidades(self, texto: str) -> dict[Prioridad, float]:
        import numpy as np

        piezas = self._tokenizador.encode(normalizar(texto))
        entradas = {"input_ids": piezas.ids, "attention_mask": piezas.attention_mask,
                    "token_type_ids": piezas.type_ids}
        datos = {nombre: np.array([valores], dtype=np.int64)
                 for nombre, valores in entradas.items() if nombre in self._entradas}
        logits = [float(x) for x in self._sesion.run(None, datos)[0][0]]
        maximo = max(logits)
        exps = [math.exp(v - maximo) for v in logits]
        total = sum(exps)
        return {c: e / total for c, e in zip(self._clases, exps, strict=True)}

    def clasificar(self, texto: str) -> Resultado:
        probs = self.probabilidades(texto)
        if probs[Prioridad.CRITICA] >= self._umbral_critica:
            elegida = Prioridad.CRITICA
        else:
            elegida = max(probs, key=probs.get)
        orden = sorted(probs, key=probs.get, reverse=True)
        # RNF-09: el Transformer no señala palabras; se dice cuánto creyó en cada opción.
        evidencias = [f"Transformer: {c.value} con probabilidad {probs[c]:.2f}"
                      for c in orden[:2]]
        return Resultado(elegida, round(probs[elegida], 2), evidencias)


@cache
def cargar_modelo_onnx(directorio: Path = DIRECTORIO) -> ModeloOnnx:
    return ModeloOnnx.desde_directorio(directorio)
