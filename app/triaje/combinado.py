"""Reglas + modelo entrenado: el modelo solo puede SUBIR la prioridad (fase 4, #95).

¿Por qué no reemplazar las reglas? El modelo se entrenó con datos sintéticos (aún no hay
reportes reales etiquetados). Las reglas están validadas por un veterinario y ya protegen
los casos críticos conocidos. Combinarlos así no puede empeorar el recall de «crítica»
(RNF-03): si las reglas ven un crítico, sigue siendo crítico; si el modelo ve algo más grave
que las reglas, sube. Igual que RN-02, ante la duda se va hacia la revisión humana.

Confianza: si el modelo sube la prioridad se usa la suya; si no, la de las reglas. Así un
texto sin señales conocidas sigue yendo a «requiere revisión» aunque el modelo esté seguro.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable

from app.triaje import modelo_onnx
from app.triaje.clasificador import ORDEN_GRAVEDAD, VERSION, Resultado, clasificar
from app.triaje.modelo import MIN_EVIDENCIAS, ModeloTriaje, cargar_modelo
from app.triaje.modelo_onnx import ModeloOnnx

log = logging.getLogger(__name__)


def combinar(reglas: Resultado, modelo: Resultado, version_modelo: str) -> Resultado:
    if ORDEN_GRAVEDAD.index(modelo.prioridad) < ORDEN_GRAVEDAD.index(reglas.prioridad):
        prioridad, confianza = modelo.prioridad, modelo.confianza
    else:
        prioridad, confianza = reglas.prioridad, reglas.confianza
    evidencias = list(dict.fromkeys(reglas.evidencias + modelo.evidencias))
    # RNF-09: al menos 3 evidencias. Si el texto da pocas, se dice qué opinó cada parte.
    for extra in (f"modelo {version_modelo}: {modelo.prioridad.value} "
                  f"({modelo.confianza:.2f})",
                  f"reglas {VERSION}: {reglas.prioridad.value} ({reglas.confianza:.2f})",
                  f"se sugiere {prioridad.value}: la más grave entre reglas y modelo"):
        if len(evidencias) < MIN_EVIDENCIAS:
            evidencias.append(extra)
    return Resultado(prioridad, confianza, evidencias)


def clasificador_combinado(modelo: ModeloTriaje | ModeloOnnx) -> Callable[[str], Resultado]:
    def clasificar_combinado(texto: str) -> Resultado:
        return combinar(clasificar(texto), modelo.clasificar(texto), modelo.version)
    return clasificar_combinado


def _cargar_transformer() -> ModeloOnnx | None:
    """Fase 7: el Transformer ONNX si sus archivos están en app/triaje/onnx/ (hoy no: ver
    docs/aprende/fase-7-transformers.md), salvo PATITAS_TRIAJE_TRANSFORMER=0 o si no carga.
    Sin archivos ni siquiera se importa onnxruntime: no gasta memoria."""
    if os.environ.get("PATITAS_TRIAJE_TRANSFORMER", "1") == "0":
        return None
    if not (modelo_onnx.DIRECTORIO / modelo_onnx.METADATOS).exists():
        return None
    try:
        return modelo_onnx.cargar_modelo_onnx(modelo_onnx.DIRECTORIO)
    except ImportError:
        log.warning("onnxruntime o tokenizers no están instalados; triaje con TF-IDF.")
    except Exception:  # archivo ausente o dañado, error de onnxruntime: nunca tumba la API
        log.exception("No se pudo cargar el Transformer de triaje; se usa el TF-IDF.")
    return None


def triaje_por_defecto() -> tuple[Callable[[str], Resultado], str]:
    """(clasificador, versión) para la API: reglas + Transformer; si no carga, reglas + TF-IDF;
    si tampoco, solo reglas. El triaje nunca se cae por el modelo (y la versión guardada lo
    dice, RF-20). Si el modelo falla o tarda AL clasificar, ServicioTriaje aplica RN-03."""
    modelo = _cargar_transformer()
    if modelo is None:
        try:
            modelo = cargar_modelo()
        except (OSError, ValueError, KeyError):
            log.exception("No se pudo cargar el modelo de triaje; se usan solo las reglas.")
            return clasificar, VERSION
    return clasificador_combinado(modelo), f"{VERSION}+{modelo.version}"
