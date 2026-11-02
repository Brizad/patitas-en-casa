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
from collections.abc import Callable

from app.triaje.clasificador import ORDEN_GRAVEDAD, VERSION, Resultado, clasificar
from app.triaje.modelo import ModeloTriaje, cargar_modelo

log = logging.getLogger(__name__)


def combinar(reglas: Resultado, modelo: Resultado, version_modelo: str) -> Resultado:
    if ORDEN_GRAVEDAD.index(modelo.prioridad) < ORDEN_GRAVEDAD.index(reglas.prioridad):
        prioridad, confianza = modelo.prioridad, modelo.confianza
    else:
        prioridad, confianza = reglas.prioridad, reglas.confianza
    # Primero las señales de las reglas (validadas por el veterinario); del modelo solo lo que
    # no repite una señal. Si no hay evidencias útiles se muestran menos, sin rellenar.
    del_modelo = [e for e in modelo.evidencias if not _repite_senal(e, reglas.evidencias)]
    evidencias = list(dict.fromkeys(reglas.evidencias + del_modelo))
    return Resultado(prioridad, confianza, evidencias)


def _repite_senal(evidencia_modelo: str, senales: list[str]) -> bool:
    """«sarna» apunta a baja repite «señal 'sarna' -> baja»."""
    if "«" not in evidencia_modelo:
        return False
    termino = evidencia_modelo.split("«")[1].split("»")[0]
    return any(f in termino or termino in f for f in map(_fragmento, senales))


def _fragmento(senal: str) -> str:
    partes = senal.split("'")
    return partes[1] if len(partes) > 2 else senal


def clasificador_combinado(modelo: ModeloTriaje) -> Callable[[str], Resultado]:
    def clasificar_combinado(texto: str) -> Resultado:
        return combinar(clasificar(texto), modelo.clasificar(texto), modelo.version)
    return clasificar_combinado


def triaje_por_defecto() -> tuple[Callable[[str], Resultado], str]:
    """(clasificador, versión) para la API. Si el modelo no carga, se sigue solo con reglas:
    el triaje nunca se cae por el modelo (y la versión guardada lo dice, RF-20)."""
    try:
        modelo = cargar_modelo()
    except (OSError, ValueError, KeyError):
        log.exception("No se pudo cargar el modelo de triaje; se usan solo las reglas.")
        return clasificar, VERSION
    return clasificador_combinado(modelo), f"{VERSION}+{modelo.version}"
