"""Persistencia de rescates y disponibilidad de rescatistas (HU-06, RN-08)."""
from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime
from typing import Protocol

from app.dominio.modelos import (
    EstadoRescate,
    FotoEvidencia,
    InformeRescate,
    Rescate,
    ResultadoRescate,
    UbicacionRescatista,
)

ACTIVOS = (EstadoRescate.EN_CAMINO, EstadoRescate.EN_SITIO)


class RescateTomado(Exception):
    """RN-08: el rescate ya tiene rescatista."""


class RescatistaOcupado(Exception):
    """RN-08: el rescatista ya tiene un rescate activo."""


class RepositorioRescates(Protocol):
    def poner_disponible(self, rescatista: str, disponible: bool) -> None: ...
    def esta_disponible(self, rescatista: str) -> bool: ...

    def poner_zona(self, rescatista: str, comunas: frozenset[int]) -> None:
        """Comunas que cubre (#46); vacío = toda la ciudad. No cambia la disponibilidad."""
        ...

    def zona(self, rescatista: str) -> frozenset[int]: ...

    def disponibles(self) -> dict[str, frozenset[int]]:
        """Correo y zona de cada rescatista disponible."""
        ...

    def marcar_escalado(self, codigo: str, momento: datetime) -> bool:
        """True solo la primera vez: así el coordinador recibe un único aviso (RF-23)."""
        ...

    def escalados(self) -> set[str]: ...

    def aceptar(self, codigo: str, rescatista: str, momento: datetime) -> Rescate:
        """Asigna el rescate en una sola operación; lanza RescateTomado o RescatistaOcupado."""
        ...

    def vigente(self, codigo: str) -> Rescate | None:
        """El rescate en curso o atendido del reporte (los liberados no cuentan)."""
        ...

    def vigentes(self) -> list[Rescate]:
        """Todos los rescates en curso o atendidos (sin los liberados), en una consulta."""
        ...

    def activo_de(self, rescatista: str) -> Rescate | None: ...

    def historial_de(self, rescatista: str) -> list[Rescate]:
        """Rescates que aceptó, del más reciente al más viejo; los liberados no cuentan."""
        ...

    def codigos_tomados(self) -> set[str]: ...

    def avanzar(self, codigo: str, rescatista: str, desde: EstadoRescate,
                hasta: EstadoRescate, momento: datetime,
                resultado: ResultadoRescate | None = None) -> bool:
        """Cambia de estado solo si el rescate es de ese rescatista y está en «desde». #498: si
        sale de «en camino», borra su ubicación en la misma operación."""
        ...

    def guardar_ubicacion(self, ubicacion: UbicacionRescatista, rescatista: str) -> bool:
        """#498: reemplaza la última posición SOLO si el rescate del código es de ese rescatista
        y sigue en camino (en una sola operación). False si no."""
        ...

    def ubicacion(self, codigo: str) -> UbicacionRescatista | None: ...

    def borrar_ubicacion(self, codigo: str) -> None: ...

    # --- #504: informe del rescate y fotos de evidencia ---------------------------------------

    def atender_con_informe(self, informe: InformeRescate,
                            fotos: list[tuple[str, bytes]]) -> bool:
        """En UNA operación: el rescate de ese rescatista pasa de «en el sitio» a «atendido» con
        el resultado del informe, y se guardan el informe y sus fotos. False si no estaba en el
        sitio con él (y entonces no guarda nada)."""
        ...

    def informe(self, codigo: str) -> InformeRescate | None: ...

    def informes_recientes(self, limite: int) -> list[InformeRescate]: ...

    def guardar_foto_reporte(self, codigo: str, tipo: str, datos: bytes,
                             momento: datetime) -> int | None:
        """La foto del ciudadano (una por reporte). None si el reporte ya tenía."""
        ...

    def fotos_de(self, codigo: str) -> list[FotoEvidencia]: ...

    def foto(self, foto_id: int) -> tuple[FotoEvidencia, bytes] | None: ...

    def fotos_de_reportes(self, codigos: list[str]) -> dict[str, int]:
        """Código -> id de la foto del ciudadano, para las miniaturas de la cola."""
        ...


class RepositorioRescatesEnMemoria:
    def __init__(self) -> None:
        self._disponibles: set[str] = set()
        self._zonas: dict[str, frozenset[int]] = {}
        self._escalados: dict[str, datetime] = {}
        self._vigentes: dict[str, Rescate] = {}  # código -> rescate no liberado
        self._ubicaciones: dict[str, UbicacionRescatista] = {}  # #498: solo la última
        self._informes: dict[str, InformeRescate] = {}  # #504
        self._fotos: dict[int, tuple[FotoEvidencia, bytes]] = {}
        self._candado = threading.Lock()

    def poner_disponible(self, rescatista: str, disponible: bool) -> None:
        (self._disponibles.add if disponible else self._disponibles.discard)(rescatista)

    def esta_disponible(self, rescatista: str) -> bool:
        return rescatista in self._disponibles

    def poner_zona(self, rescatista: str, comunas: frozenset[int]) -> None:
        self._zonas[rescatista] = frozenset(comunas)

    def zona(self, rescatista: str) -> frozenset[int]:
        return self._zonas.get(rescatista, frozenset())

    def disponibles(self) -> dict[str, frozenset[int]]:
        return {correo: self.zona(correo) for correo in self._disponibles}

    def marcar_escalado(self, codigo: str, momento: datetime) -> bool:
        with self._candado:
            if codigo in self._escalados:
                return False
            self._escalados[codigo] = momento
            return True

    def escalados(self) -> set[str]:
        return set(self._escalados)

    def aceptar(self, codigo: str, rescatista: str, momento: datetime) -> Rescate:
        with self._candado:
            if codigo in self._vigentes:
                raise RescateTomado(codigo)
            if self._activo(rescatista) is not None:
                raise RescatistaOcupado(rescatista)
            rescate = Rescate(codigo=codigo, rescatista=rescatista,
                              estado=EstadoRescate.EN_CAMINO, aceptado_en=momento,
                              actualizado_en=momento)
            self._vigentes[codigo] = rescate
            return replace(rescate)

    def vigente(self, codigo: str) -> Rescate | None:
        rescate = self._vigentes.get(codigo)
        return replace(rescate) if rescate else None

    def vigentes(self) -> list[Rescate]:
        return [replace(r) for r in self._vigentes.values()]

    def _activo(self, rescatista: str) -> Rescate | None:
        return next((r for r in self._vigentes.values()
                     if r.rescatista == rescatista and r.estado in ACTIVOS), None)

    def activo_de(self, rescatista: str) -> Rescate | None:
        rescate = self._activo(rescatista)
        return replace(rescate) if rescate else None

    def historial_de(self, rescatista: str) -> list[Rescate]:
        propios = [replace(r) for r in self._vigentes.values() if r.rescatista == rescatista]
        return sorted(propios, key=lambda r: r.aceptado_en, reverse=True)

    def codigos_tomados(self) -> set[str]:
        return set(self._vigentes)

    def avanzar(self, codigo: str, rescatista: str, desde: EstadoRescate,
                hasta: EstadoRescate, momento: datetime,
                resultado: ResultadoRescate | None = None) -> bool:
        with self._candado:
            rescate = self._vigentes.get(codigo)
            if rescate is None or rescate.rescatista != rescatista or rescate.estado != desde:
                return False
            if hasta != EstadoRescate.EN_CAMINO:
                self._ubicaciones.pop(codigo, None)  # #498
            if hasta == EstadoRescate.LIBERADO:
                del self._vigentes[codigo]
                return True
            rescate.estado, rescate.resultado, rescate.actualizado_en = hasta, resultado, momento
            if hasta == EstadoRescate.EN_SITIO:
                rescate.llegada_en = momento
            return True

    def guardar_ubicacion(self, ubicacion: UbicacionRescatista, rescatista: str) -> bool:
        with self._candado:
            rescate = self._vigentes.get(ubicacion.codigo)
            if (rescate is None or rescate.rescatista != rescatista
                    or rescate.estado != EstadoRescate.EN_CAMINO):
                return False
            self._ubicaciones[ubicacion.codigo] = ubicacion
            return True

    def ubicacion(self, codigo: str) -> UbicacionRescatista | None:
        return self._ubicaciones.get(codigo)

    def borrar_ubicacion(self, codigo: str) -> None:
        with self._candado:
            self._ubicaciones.pop(codigo, None)

    # --- #504 ------------------------------------------------------------------------------

    def _nueva_foto(self, codigo: str, origen: str, tipo: str, datos: bytes,
                    momento: datetime) -> int:
        foto_id = len(self._fotos) + 1
        self._fotos[foto_id] = (FotoEvidencia(foto_id, codigo, origen, tipo, momento), datos)
        return foto_id

    def atender_con_informe(self, informe: InformeRescate,
                            fotos: list[tuple[str, bytes]]) -> bool:
        with self._candado:
            rescate = self._vigentes.get(informe.codigo)
            if (rescate is None or rescate.rescatista != informe.rescatista
                    or rescate.estado != EstadoRescate.EN_SITIO):
                return False
            rescate.estado, rescate.resultado = EstadoRescate.ATENDIDO, informe.resultado
            rescate.actualizado_en = informe.creado_en
            self._informes[informe.codigo] = informe
            for tipo, datos in fotos:
                self._nueva_foto(informe.codigo, "rescate", tipo, datos, informe.creado_en)
            return True

    def informe(self, codigo: str) -> InformeRescate | None:
        return self._informes.get(codigo)

    def informes_recientes(self, limite: int) -> list[InformeRescate]:
        return sorted(self._informes.values(), key=lambda i: i.creado_en, reverse=True)[:limite]

    def guardar_foto_reporte(self, codigo: str, tipo: str, datos: bytes,
                             momento: datetime) -> int | None:
        with self._candado:
            if any(f.codigo == codigo and f.origen == "reporte" for f, _ in self._fotos.values()):
                return None
            return self._nueva_foto(codigo, "reporte", tipo, datos, momento)

    def fotos_de(self, codigo: str) -> list[FotoEvidencia]:
        return sorted((f for f, _ in self._fotos.values() if f.codigo == codigo),
                      key=lambda f: f.id)

    def foto(self, foto_id: int) -> tuple[FotoEvidencia, bytes] | None:
        return self._fotos.get(foto_id)

    def fotos_de_reportes(self, codigos: list[str]) -> dict[str, int]:
        buscados = set(codigos)
        return {f.codigo: f.id for f, _ in self._fotos.values()
                if f.origen == "reporte" and f.codigo in buscados}
