"""Límite de intentos fallidos de inicio de sesión (DT-06) y de registros por IP (DT-09).

Cada fallo se guarda con una clave ("correo:<correo>" o "ip:<ip>") y la hora en que ocurrió.
Una clave con el máximo de fallos dentro de la ventana queda bloqueada hasta que el fallo más
antiguo de los que cuentan salga de la ventana. Nunca se guarda ni se registra la contraseña.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.config import (
    INTENTOS_MAXIMOS,
    INTENTOS_MAXIMOS_POR_IP,
    REGISTROS_MAXIMOS_POR_IP,
    VENTANA_INTENTOS_MINUTOS,
)


class RepositorioIntentos(Protocol):
    def registrar_fallo(self, clave: str, momento: datetime) -> None: ...

    def fallos_desde(self, clave: str, desde: datetime) -> list[datetime]:
        """Horas de los fallos de la clave posteriores a «desde», de la más antigua a la
        más reciente."""
        ...

    def limpiar(self, clave: str) -> None: ...

    def purgar_antes_de(self, momento: datetime) -> None:
        """Borra los fallos de todas las claves anteriores a «momento» (ya no cuentan)."""
        ...


class RepositorioIntentosEnMemoria:
    def __init__(self) -> None:
        self._fallos: dict[str, list[datetime]] = {}

    def registrar_fallo(self, clave: str, momento: datetime) -> None:
        self._fallos.setdefault(clave, []).append(momento)

    def fallos_desde(self, clave: str, desde: datetime) -> list[datetime]:
        return sorted(m for m in self._fallos.get(clave, []) if m > desde)

    def limpiar(self, clave: str) -> None:
        self._fallos.pop(clave, None)

    def purgar_antes_de(self, momento: datetime) -> None:
        for clave in list(self._fallos):
            self._fallos[clave] = [m for m in self._fallos[clave] if m >= momento]
            if not self._fallos[clave]:
                del self._fallos[clave]


def clave_correo(correo: str) -> str:
    return f"correo:{correo}"


def clave_ip(ip: str) -> str:
    return f"ip:{ip}"


def clave_registro(ip: str) -> str:
    """DT-09 (#149): cada registro público cuenta, salga bien o no."""
    return f"registro:{ip}"


class LimiteIntentos:
    def __init__(self, repositorio: RepositorioIntentos, *, maximo: int = INTENTOS_MAXIMOS,
                 ventana: timedelta = timedelta(minutes=VENTANA_INTENTOS_MINUTOS),
                 maximos: Mapping[str, int] | None = None,
                 reloj: Callable[[], datetime] | None = None) -> None:
        """«maximos» cambia el máximo por tipo de clave, p. ej. {"ip": 20}."""
        self._maximos = ({"ip": INTENTOS_MAXIMOS_POR_IP, "registro": REGISTROS_MAXIMOS_POR_IP}
                         if maximos is None else dict(maximos))
        if maximo < 1 or any(m < 1 for m in self._maximos.values()):
            raise ValueError("El máximo de intentos debe ser 1 o más.")
        self._repositorio = repositorio
        self._maximo = maximo
        self._ventana = ventana
        self._reloj = reloj or (lambda: datetime.now(UTC))

    def _maximo_de(self, clave: str) -> int:
        return self._maximos.get(clave.split(":", 1)[0], self._maximo)

    def segundos_de_bloqueo(self, claves: Iterable[str]) -> int:
        """0 si se puede intentar; si no, segundos que faltan para el próximo intento."""
        ahora = self._reloj()
        espera = 0
        for clave in claves:
            fallos = self._repositorio.fallos_desde(clave, ahora - self._ventana)
            maximo = self._maximo_de(clave)
            if len(fallos) >= maximo:
                # Cuando este fallo salga de la ventana quedarán maximo - 1: se libera uno.
                libera = fallos[len(fallos) - maximo] + self._ventana
                espera = max(espera, math.ceil((libera - ahora).total_seconds()), 1)
        return espera

    def registrar_fallo(self, claves: Iterable[str]) -> None:
        ahora = self._reloj()
        self._repositorio.purgar_antes_de(ahora - self._ventana)
        for clave in claves:
            self._repositorio.registrar_fallo(clave, ahora)

    def registrar_exito(self, clave: str) -> None:
        self._repositorio.limpiar(clave)
