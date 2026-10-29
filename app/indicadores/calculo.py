"""Indicadores del sistema (RF-30, fase 5, #102).

Funciones puras sobre los datos que ya existen: no hay tablas nuevas ni almacén de datos (el
documento de arquitectura dice que con pocos datos bastan consultas sobre la base
principal). Ningún indicador lleva datos personales: solo conteos, porcentajes y tiempos.

El «acuerdo por versión del modelo» usa RF-20: cuántas veces el veterinario confirmó la
prioridad que sugirió cada versión. Es la señal para saber si un modelo nuevo ayuda.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import median

from app.adopciones.modelos import EstadoSolicitud, Seguimiento, Solicitud
from app.dominio.modelos import DecisionTriaje, Refugio, Reporte, Rescate


@dataclass(frozen=True)
class Datos:
    reportes: list[Reporte]
    decisiones: dict[str, DecisionTriaje]  # código → decisión (confirmados)
    rescates: list[Rescate]
    refugios: list[Refugio]
    solicitudes: list[Solicitud]
    seguimientos: list[Seguimiento]


def _contar(valores: Iterable) -> dict[str, int]:
    return dict(sorted(Counter(str(v) for v in valores).items()))


def calcular(d: Datos, ahora) -> dict:
    por_codigo = {r.codigo: r for r in d.reportes}
    minutos = [(dec.decidido_en - por_codigo[c].creado_en).total_seconds() / 60
               for c, dec in d.decisiones.items() if c in por_codigo]
    acuerdo: dict[str, list[bool]] = {}
    for c, dec in d.decisiones.items():
        version = (por_codigo[c].version_modelo if c in por_codigo else None) or "sin versión"
        acuerdo.setdefault(version, []).append(not dec.ajustada)
    pendientes = [s for s in d.seguimientos if s.realizado_en is None]
    return {
        "reportes": {
            "total": len(d.reportes),
            "por_estado": _contar(r.estado.value for r in d.reportes),
            "por_prioridad_confirmada": _contar(x.prioridad_final.value
                                                for x in d.decisiones.values()),
            "minutos_hasta_confirmar": {
                "mediana": round(median(minutos), 1) if minutos else None,
                "promedio": round(sum(minutos) / len(minutos), 1) if minutos else None},
            "acuerdo_por_version_modelo": {
                v: {"decisiones": len(x), "confirmadas_sin_cambio": round(sum(x) / len(x), 3)}
                for v, x in sorted(acuerdo.items())},
        },
        "rescates": {
            "por_estado": _contar(r.estado.value for r in d.rescates),
            "por_resultado": _contar(r.resultado.value for r in d.rescates if r.resultado),
        },
        "refugios": [{"nombre": r.nombre, "ocupados": r.ocupados, "capacidad": r.capacidad,
                      "porcentaje": round(r.porcentaje_ocupacion() * 100, 1)}
                     for r in d.refugios],
        "adopciones": {
            "solicitudes_por_estado": _contar(s.estado.value for s in d.solicitudes),
            "aprobadas": sum(s.estado == EstadoSolicitud.APROBADA for s in d.solicitudes),
            "seguimientos": {
                "hechos": len(d.seguimientos) - len(pendientes),
                "pendientes": sum(s.programado_para >= ahora for s in pendientes),
                "vencidos": sum(s.programado_para < ahora for s in pendientes)},
        },
    }
