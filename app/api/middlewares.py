"""Middlewares y ciclo de vida de la API (#282): antes vivían dentro de crear_app."""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from app import config
from app.bitacora.repositorio import Evento, RepositorioBitacora
from app.seguridad.tokens import EmisorTokens, TokenInvalido
from app.tareas_de_fondo import TareaDeFondo

logger = logging.getLogger("app.api.main")  # el mismo de antes: los logs no cambian

# Solo recursos del propio servidor: sin scripts en línea ni de terceros (XSS).
POLITICA_PERMISOS = "geolocation=(self), camera=(self), microphone=(), payment=()"
POLITICA_PWA = ("default-src 'self'; script-src 'self'; style-src 'self'; "
                # #125: blob: son archivos locales del navegador (la tira del video en el panel
                # y la duración del video elegido en la PWA); nunca de otro servidor.
                # #430: el mapa (Leaflet) pide teselas de OpenStreetMap; solo imágenes, solo ese
                # servidor. Ningún script ni estilo viene de fuera.
                "img-src 'self' blob: https://tile.openstreetmap.org; media-src blob:; "
                "connect-src 'self'; manifest-src 'self'; worker-src 'self'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")

# A-01 (#235): el video, la vista previa y las fotos llegan por partes y tienen su propio tope.
_SUBIDAS_DE_ARCHIVO = re.compile(r"^/(reportes/[^/]+/video|video/trabajos/\d+/vista"
                                 r"|refugio/animales/\d+/foto)$")


def es_subida_de_archivo(ruta: str) -> bool:
    return _SUBIDAS_DE_ARCHIVO.match(ruta) is not None


class LimiteCuerpoSinLargo:
    """A-08 (#283): una petición *chunked* no trae Content-Length, así que limitar_cuerpo no
    puede rechazarla de entrada. Aquí se cuentan los bytes a medida que llegan y, al pasar el
    tope, la lectura del cuerpo falla con 413 (FastAPI lo responde como cualquier HTTPException)
    sin guardar el resto en memoria. Las subidas de archivos tienen su propio tope."""

    def __init__(self, app, maximo: int = config.MAX_CUERPO_BYTES) -> None:
        self.app = app
        self.maximo = maximo

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or es_subida_de_archivo(scope["path"])
                or any(nombre == b"content-length" for nombre, _ in scope["headers"])):
            return await self.app(scope, receive, send)
        leidos = 0

        async def recibir():
            nonlocal leidos
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                leidos += len(mensaje.get("body", b""))
                if leidos > self.maximo:
                    raise HTTPException(413, "La petición es demasiado grande.")
            return mensaje

        await self.app(scope, recibir, send)


def ciclo_de_vida(de_fondo: list[TareaDeFondo], motor: Engine | None):
    """Arranca las tareas de fondo (#390: solo consultan la base cuando hay trabajo) y, al
    apagar, las detiene y cierra la base."""
    @asynccontextmanager
    async def ciclo(_app: FastAPI) -> AsyncIterator[None]:
        tareas = [asyncio.create_task(tarea.correr()) for tarea in de_fondo]
        yield
        for tarea in tareas:
            tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarea
        if motor is not None:
            motor.dispose()
    return ciclo


def instalar_despertador(app: FastAPI, de_fondo: list[TareaDeFondo]) -> None:
    """#390: toda petición que cambia datos y sale bien despierta las tareas de fondo (por
    ejemplo, confirmar guarda avisos y ofrece un rescate). La base ya está despierta por la
    propia petición, así que revisar en ese momento no le suma minutos a Neon."""
    @app.middleware("http")
    async def despertar_tareas(peticion: Request, siguiente):
        respuesta = await siguiente(peticion)
        if (peticion.method in ("POST", "PUT", "PATCH", "DELETE")
                and 200 <= respuesta.status_code < 300
                # El sondeo del nodo sin trabajos (204) no cambia nada.
                and not (respuesta.status_code == 204
                         and peticion.url.path == "/video/trabajos/reclamar")):
            for tarea in de_fondo:
                tarea.despertar()
        return respuesta


# Parte 7c: el commit que Render desplegó (variable que Render pone sola). «Verificar despliegue»
# lo compara con el commit unido a main; la versión de pyproject no cambia en cada PR.
COMMIT_DESPLEGADO = os.environ.get("RENDER_GIT_COMMIT", "").strip()


def poner_cabeceras(peticion: Request, respuesta):
    """Cabeceras de seguridad de toda respuesta (#121, ASVS 8.2.1 y 14.4)."""
    # Prueba de punta a punta (#121, OWASP ZAP): en todas las respuestas, HTTPS por un año
    # (HSTS), el GPS y la cámara solo desde este sitio (la PWA los usa; #212), sin micrófono, y
    # ninguna otra ventana puede manipular esta (COOP).
    respuesta.headers["Strict-Transport-Security"] = "max-age=31536000"
    respuesta.headers["Permissions-Policy"] = POLITICA_PERMISOS
    respuesta.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if COMMIT_DESPLEGADO:  # el código es abierto: decir qué commit corre no expone nada
        respuesta.headers["X-Version-Commit"] = COMMIT_DESPLEGADO
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    # ASVS 14.4.6 y 14.4.7: ninguna respuesta (tampoco la API ni /docs) se puede meter en
    # un marco de otro sitio ni le cuenta a otro sitio de qué página venía el usuario.
    respuesta.headers.setdefault("Referrer-Policy", "no-referrer")
    respuesta.headers.setdefault("X-Frame-Options", "DENY")
    # ASVS 8.2.1: los datos de la API (reportes, personas, sesiones) no se guardan en el
    # navegador ni en proxies. Lo que ya dice cómo guardarse (fotos, estáticos) no cambia.
    if respuesta.headers.get("content-type", "").startswith("application/json"):
        respuesta.headers.setdefault("Cache-Control", "no-store")
    if peticion.url.path == "/" or peticion.url.path.startswith(("/app", "/panel",
                                                              "/inicio", "/diseno")):
        respuesta.headers["Content-Security-Policy"] = POLITICA_PWA
    return respuesta


def instalar_middlewares(app: FastAPI, repositorio_bitacora: RepositorioBitacora,
                         emisor_tokens: EmisorTokens, token_video: str | None) -> None:
    """Tope del cuerpo (A-01, A-08), cabeceras de seguridad (#121) y bitácora (RF-32)."""
    app.add_middleware(LimiteCuerpoSinLargo)

    @app.middleware("http")
    async def limitar_cuerpo(peticion: Request, siguiente):
        """A-01 (#235): un cuerpo enorme se rechaza antes de leerlo (Render tiene 512 MB)."""
        largo = peticion.headers.get("content-length", "")
        if (largo.isdigit() and int(largo) > config.MAX_CUERPO_BYTES
                and not es_subida_de_archivo(peticion.url.path)):
            return JSONResponse({"detail": "La petición es demasiado grande."}, status_code=413)
        return await siguiente(peticion)

    @app.middleware("http")
    async def cabeceras_de_la_pwa(peticion: Request, siguiente):
        return poner_cabeceras(peticion, await siguiente(peticion))

    @app.middleware("http")
    async def registrar_en_bitacora(peticion: Request, siguiente):
        """RF-32: toda petición que cambia datos y sale bien queda en la bitácora. Se guarda
        la PLANTILLA de la ruta y sus parámetros, nunca el cuerpo (contraseñas, datos
        personales). El inicio de sesión no cambia datos y ya lo cuenta DT-06."""
        respuesta = await siguiente(peticion)
        ruta = peticion.scope.get("route")
        if (peticion.method in ("POST", "PUT", "PATCH", "DELETE")
                and 200 <= respuesta.status_code < 300 and ruta is not None
                and ruta.path != "/auth/token"):
            # #125: el sondeo del trabajador sin trabajos (204) no es una acción.
            if respuesta.status_code == 204 and ruta.path == "/video/trabajos/reclamar":
                return respuesta
            clave_video = peticion.headers.get("x-video-token", "")
            actor = ("trabajador de video" if token_video and clave_video
                     and hmac.compare_digest(clave_video, token_video) else "anónimo")
            token = peticion.headers.get("authorization", "").removeprefix("Bearer ")
            if token:
                with contextlib.suppress(TokenInvalido):
                    actor = emisor_tokens.validar(token).correo
            try:
                # En un hilo: el INSERT no debe frenar las demás peticiones (async).
                anterior, nuevo = getattr(peticion.state, "cambio", (None, None))
                await run_in_threadpool(repositorio_bitacora.registrar, Evento(
                    actor, f"{peticion.method} {ruta.path}",
                    {k: str(v) for k, v in peticion.path_params.items()},
                    respuesta.status_code, anterior=anterior, nuevo=nuevo))
            except Exception:
                # La acción ya ocurrió; no se le dice al usuario que falló. Queda en el log.
                logger.exception("No se pudo registrar en la bitácora: %s", ruta.path)
        return respuesta
