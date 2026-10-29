"""Línea de tiempo del reporte para el ciudadano (HU-08, RF-11, RN-14).

Pasos y textos del prototipo (docs/prototipo/interaccion.js, "3. Consultar estado"). RN-14:
solo el código, las fechas y los pasos; nunca descripción, ubicación, prioridad ni personas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.dominio.modelos import (
    DecisionTriaje,
    EstadoReporte,
    EstadoRescate,
    Prioridad,
    Reporte,
    Rescate,
    ResultadoRescate,
)

RESULTADOS = {
    ResultadoRescate.TRASLADADO: "Trasladado a refugio",
    ResultadoRescate.ATENDIDO_EN_SITIO: "Atendido en el sitio",
    ResultadoRescate.NO_ENCONTRADO: "No encontrado",
    ResultadoRescate.FALLECIDO: "Fallecido",
}


@dataclass(frozen=True)
class Paso:
    nombre: str
    estado: str  # "hecho", "actual" o "pendiente"
    detalle: str | None
    fecha: datetime | None


def normalizar_codigo(codigo: str) -> str:
    """El ciudadano puede escribirlo en minúsculas o separado ("F2HW 5RTB")."""
    return "".join(codigo.split()).upper()


def linea_de_tiempo(reporte: Reporte, decision: DecisionTriaje | None,
                    rescate: Rescate | None,
                    descartado_en: datetime | None = None) -> tuple[list[Paso], datetime]:
    if reporte.estado == EstadoReporte.DESCARTADO and descartado_en is not None:
        # D-02: el ciudadano ve que se revisó y se cerró, sin el motivo ni el original del
        # duplicado (RN-14: nada que apunte a otro reporte ni a personas).
        return ([Paso("Recibido", "hecho", None, _utc(reporte.creado_en)),
                 Paso("Descartado", "hecho", "Revisado: no requiere una nueva atención",
                      _utc(descartado_en))], _utc(descartado_en))
    confirmado = reporte.estado == EstadoReporte.CONFIRMADO
    de_rescate = confirmado and reporte.prioridad in (Prioridad.CRITICA, Prioridad.ALTA)
    atendido = rescate is not None and rescate.estado == EstadoRescate.ATENDIDO
    nombres = [
        "Recibido",
        "Revisado por el veterinario",
        "Atención programada por el refugio" if confirmado and not de_rescate
        else "Rescatista en camino",
        f"Atendido · {RESULTADOS[rescate.resultado]}" if atendido else "Atendido",
        "Cerrado",
    ]
    revisado = decision.decidido_en if decision else None
    fechas = [reporte.creado_en, revisado,
              rescate.aceptado_en if rescate else revisado,
              rescate.actualizado_en if atendido else None,
              rescate.actualizado_en if atendido else None]

    # Paso actual (índice en nombres); 5 = todos hechos. Igual que el prototipo.
    if atendido:
        actual, detalle = 5, None
    elif rescate is not None and rescate.estado == EstadoRescate.EN_SITIO:
        actual, detalle = 3, "Rescatista en el sitio"
    elif confirmado:
        actual = 2
        detalle = "Buscando rescatista disponible" if de_rescate and rescate is None else None
    else:
        actual, detalle = 1, None

    pasos = [Paso(nombre,
                  "hecho" if i < actual else "actual" if i == actual else "pendiente",
                  detalle if i == actual else None,
                  _utc(fechas[i]) if i < actual else None)
             for i, nombre in enumerate(nombres)]
    momentos = [reporte.creado_en, revisado]
    if rescate is not None:
        momentos.append(rescate.actualizado_en)
    return pasos, max(_utc(m) for m in momentos if m is not None)


def _utc(momento: datetime | None) -> datetime | None:
    return momento.astimezone(UTC) if momento else None
