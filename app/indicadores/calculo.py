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

from app.adopciones.compatibilidad import calcular as compatibilidad
from app.adopciones.modelos import (
    EstadoSolicitud,
    PerfilAdoptante,
    Publicacion,
    Seguimiento,
    Solicitud,
)
from app.dominio.modelos import DecisionTriaje, Refugio, Reporte, Rescate


@dataclass(frozen=True)
class Datos:
    reportes: list[Reporte]
    decisiones: dict[str, DecisionTriaje]  # código → decisión (confirmados)
    rescates: list[Rescate]
    refugios: list[Refugio]
    solicitudes: list[Solicitud]
    seguimientos: list[Seguimiento]
    perfiles: tuple[PerfilAdoptante, ...] = ()  # RNF-16
    disponibles: tuple[Publicacion, ...] = ()


def _mediana(valores: list[float]) -> float | None:
    return round(median(valores), 1) if valores else None


def _por_prioridad(d: Datos) -> dict[str, dict[str, float | None]]:
    """RF-30: tiempo de respuesta por prioridad confirmada: hasta confirmar y, en críticos y
    altos, desde la confirmación hasta que un rescatista aceptó."""
    por_codigo = {r.codigo: r for r in d.reportes}
    rescates = {r.codigo: r for r in d.rescates}
    grupos: dict[str, dict[str, list[float]]] = {}
    for c, dec in d.decisiones.items():
        if c not in por_codigo:
            continue
        g = grupos.setdefault(dec.prioridad_final.value, {"confirmar": [], "aceptar": []})
        g["confirmar"].append((dec.decidido_en - por_codigo[c].creado_en).total_seconds() / 60)
        if c in rescates:
            g["aceptar"].append((rescates[c].aceptado_en - dec.decidido_en).total_seconds() / 60)
    return {p: {"mediana_minutos_hasta_confirmar": _mediana(g["confirmar"]),
                "mediana_minutos_hasta_aceptar_rescate": _mediana(g["aceptar"])}
            for p, g in sorted(grupos.items())}


def _tasa_por_segmento(d: Datos) -> dict[str, dict[str, float | int]]:
    """RNF-16: qué fracción del catálogo se le recomienda, en promedio, a cada grupo de
    hogares. Una diferencia grande entre grupos es una señal para revisar los pesos. Los
    grupos son características del hogar (no de la persona: no hay atributos protegidos)."""
    if not d.disponibles:
        return {}
    segmentos: dict[str, list[float]] = {}
    for p in d.perfiles:
        tasa = sum(compatibilidad(p, a).recomendable for a in d.disponibles) / len(d.disponibles)
        for clave in (f"vivienda: {p.vivienda.value}",
                      "con niños" if p.hay_ninos else "sin niños",
                      "con otros animales" if p.otros_animales else "sin otros animales"):
            segmentos.setdefault(clave, []).append(tasa)
    return {k: {"perfiles": len(v), "tasa_recomendacion": round(sum(v) / len(v), 3)}
            for k, v in sorted(segmentos.items())}


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
            "tiempos_por_prioridad": _por_prioridad(d),
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
            "devoluciones": sum(s.estado == EstadoSolicitud.DEVUELTA for s in d.solicitudes),
            "tasa_recomendacion_por_segmento": _tasa_por_segmento(d),
            "seguimientos": {
                "hechos": len(d.seguimientos) - len(pendientes),
                "pendientes": sum(s.programado_para >= ahora for s in pendientes),
                "vencidos": sum(s.programado_para < ahora for s in pendientes)},
        },
    }
