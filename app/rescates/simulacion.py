"""Recorrido de demostración (#498): el SERVIDOR mueve la posición del rescatista desde ~1,5 km
hasta el animal, por el mismo camino que una ubicación real (ServicioRescates.compartir_ubicacion,
marcada «simulada»). Así cualquier pestaña del ciudadano lo ve moverse igual que en la vida real.

Solo para las cuentas de demostración (dominio de app/demo.py); para cualquier otra, 403. Al
llegar espera unos segundos («¡Está llegando!») y marca el caso atendido en el sitio.
"""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from app import config
from app.demo import DOMINIO
from app.dominio.modelos import ResultadoRescate, Usuario
from app.reportes.repositorio import RepositorioReportes
from app.rescates.distancia import desplazar
from app.rescates.servicio import PasoInvalido, ServicioRescates, SinPermiso

log = logging.getLogger(__name__)

DISTANCIA_INICIAL_M = 1500
RUMBO_INICIAL = 45  # llega desde el nororiente


def es_cuenta_demo(usuario: Usuario) -> bool:
    return usuario.correo.endswith(f"@{DOMINIO}")


class Simulaciones:
    def __init__(self, servicio: ServicioRescates, reportes: RepositorioReportes,
                 dormir: Callable[[float], None] = time.sleep) -> None:
        self._servicio = servicio
        self._reportes = reportes
        self._dormir = dormir
        self._en_curso: set[str] = set()
        self._candado = threading.Lock()

    def iniciar(self, rescatista: Usuario, codigo: str, en_hilo: bool = True) -> int:
        """Valida y arranca el recorrido; devuelve cuántos segundos dura."""
        if not es_cuenta_demo(rescatista):
            raise SinPermiso(
                "El recorrido de demostración es solo para las cuentas de demostración.")
        self._servicio.exigir_en_camino(rescatista, codigo)
        reporte = self._reportes.buscar(codigo)
        lat, lon = reporte.ubicacion.latitud, reporte.ubicacion.longitud
        if lat is None or lon is None:
            raise PasoInvalido("El reporte no tiene ubicación GPS para simular el recorrido.")
        with self._candado:
            if codigo in self._en_curso:
                raise PasoInvalido("El recorrido de demostración ya está en marcha.")
            self._en_curso.add(codigo)
        if en_hilo:
            threading.Thread(target=self.correr, args=(rescatista, codigo, lat, lon),
                             daemon=True, name=f"simulacion-{codigo}").start()
        else:
            self.correr(rescatista, codigo, lat, lon)
        return config.SIMULACION_SEGUNDOS

    def correr(self, rescatista: Usuario, codigo: str, lat: float, lon: float) -> None:
        intervalo = config.SIMULACION_INTERVALO_S
        pasos = max(1, round(config.SIMULACION_SEGUNDOS / max(intervalo, 0.001)))
        inicio = desplazar(lat, lon, DISTANCIA_INICIAL_M, RUMBO_INICIAL)
        try:
            for i in range(pasos + 1):
                f = i / pasos
                self._servicio.compartir_ubicacion(
                    rescatista, codigo, inicio[0] + (lat - inicio[0]) * f,
                    inicio[1] + (lon - inicio[1]) * f, simulada=True)
                if i < pasos:
                    self._dormir(intervalo)
            self._dormir(config.SIMULACION_ESPERA_LLEGADA_S)  # «¡Está llegando!»
            self._servicio.llegue(rescatista, codigo)
            self._servicio.registrar_resultado(rescatista, codigo,
                                               ResultadoRescate.ATENDIDO_EN_SITIO)
        except (PasoInvalido, SinPermiso):
            pass  # el rescatista llegó, liberó o atendió a mano: el recorrido termina ahí
        except Exception:  # un hilo de fondo nunca debe caer en silencio
            log.exception("Falló el recorrido de demostración de %s.", codigo)
        finally:
            with self._candado:
                self._en_curso.discard(codigo)
