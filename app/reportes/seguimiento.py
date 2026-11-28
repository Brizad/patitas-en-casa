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

# #504: el ciudadano ve solo el resultado, en lenguaje amable (nunca la nota ni las fotos).
RESULTADOS = {
    ResultadoRescate.TRASLADADO: "Lo trasladamos al refugio",
    ResultadoRescate.ATENDIDO_EN_SITIO: "Lo atendimos en el lugar",
    ResultadoRescate.VETERINARIA: "Lo llevamos a una veterinaria",
    ResultadoRescate.NO_ENCONTRADO: "No encontramos al animal en el lugar",
    ResultadoRescate.NO_RESCATADO: "No pudimos rescatarlo",
    ResultadoRescate.FALLECIDO: "Lamentablemente falleció",
}
LLEGADA = "El rescatista llegó al lugar"


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
                    descartado_en: datetime | None = None,
                    archivado: bool = False) -> tuple[list[Paso], datetime]:
    if reporte.estado == EstadoReporte.DESCARTADO and descartado_en is not None and archivado:
        # #496: atrasado que no se pudo verificar; el ciudadano lo ve cerrado, sin el motivo.
        return ([Paso("Recibido", "hecho", None, _utc(reporte.creado_en)),
                 Paso("Cerrado", "hecho", "No pudimos verificar el reporte",
                      _utc(descartado_en))], _utc(descartado_en))
    if reporte.estado == EstadoReporte.DESCARTADO and descartado_en is not None:
        # D-02: el ciudadano ve que se revisó y se cerró, sin el motivo ni el original del
        # duplicado (RN-14: nada que apunte a otro reporte ni a personas).
        return ([Paso("Recibido", "hecho", None, _utc(reporte.creado_en)),
                 Paso("Descartado", "hecho", "Revisado: no requiere una nueva atención",
                      _utc(descartado_en))], _utc(descartado_en))
    confirmado = reporte.estado == EstadoReporte.CONFIRMADO
    de_rescate = confirmado and reporte.prioridad in (Prioridad.CRITICA, Prioridad.ALTA)
    atendido = rescate is not None and rescate.estado == EstadoRescate.ATENDIDO
    programada = confirmado and not de_rescate  # media o baja: la atiende el refugio
    revisado = decision.decidido_en if decision else None
    # #504: con rescatista, el paso «El rescatista llegó al lugar» y su hora real.
    pasos_base = [
        ("Recibido", reporte.creado_en),
        ("Revisado por el veterinario", revisado),
        ("Atención programada por el refugio" if programada else "Rescatista en camino",
         rescate.aceptado_en if rescate else revisado),
        *([] if programada else [(LLEGADA, rescate.llegada_en if rescate else None)]),
        (f"Atendido · {RESULTADOS[rescate.resultado]}" if atendido else "Atendido",
         rescate.actualizado_en if atendido else None),
        ("Cerrado", rescate.actualizado_en if atendido else None),
    ]
    nombres = [n for n, _ in pasos_base]
    fechas = [f for _, f in pasos_base]
    ultimo = len(nombres) - 1  # «Cerrado»

    # Paso actual (índice en nombres); len(nombres) = todos hechos. Igual que el prototipo.
    if atendido:
        actual, detalle = len(nombres), None
    elif rescate is not None and rescate.estado == EstadoRescate.EN_SITIO:
        actual, detalle = ultimo - 1, "El rescatista está con el animal"
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
