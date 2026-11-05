"""Lo que comparten los routers de la API (DT-13, #267).

`crear_app` arma los repositorios, los servicios y las dependencias de rol una sola vez y los
reúne en un `Contexto`. Cada módulo de rutas (`app/api/rutas_*.py`) recibe ese contexto y toma
lo que necesita; así ningún router repite treinta parámetros y las rutas no cambian.
"""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import Request


def ip_del_cliente(peticion: Request, ajustes) -> str:
    """A-04 / DT-11 (#278): la IP para los límites por IP (DT-06, DT-09, A-02).

    Primero el encabezado que escribe el proxy (si está configurado y viene); si no, la
    entrada N desde la derecha de X-Forwarded-For (las que agregan los N proxies de confianza;
    la de la izquierda la puede inventar el cliente); si no, la IP de la conexión.
    """
    if ajustes.encabezado_ip:
        valor = peticion.headers.get(ajustes.encabezado_ip.lower(), "").strip()
        if valor:
            return valor
    if ajustes.proxies_confianza:
        lista = [x.strip() for x in peticion.headers.get("x-forwarded-for", "").split(",")
                 if x.strip()]
        if len(lista) >= ajustes.proxies_confianza:
            return lista[-ajustes.proxies_confianza]
    return peticion.client.host if peticion.client else "desconocida"


class Contexto(SimpleNamespace):
    """Servicios, repositorios y dependencias de `crear_app`, con los mismos nombres."""


def fecha_utc(fecha: datetime | None) -> str | None:
    """D-06: toda fecha de la API sale en UTC («+00:00»). PostgreSQL devuelve la hora en la
    zona de la sesión (en Cúcuta, -05:00): es el mismo instante, pero dos formatos confunden."""
    return None if fecha is None else fecha.astimezone(UTC).isoformat()


def cambiar(peticion: Request, anterior: dict | None, nuevo: dict | None) -> None:
    """RNF-12 (#149): el endpoint deja aquí cómo estaba y cómo quedó; el middleware de la
    bitácora lo guarda junto con el actor y la ruta. Solo estados y cifras, nunca datos
    personales ni el cuerpo de la petición."""
    peticion.state.cambio = (anterior, nuevo)
