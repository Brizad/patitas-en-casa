"""Middlewares y ciclo de vida de la API (#282): antes vivían dentro de crear_app."""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
import re
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from app import config
from app.bitacora.repositorio import Evento, RepositorioBitacora
from app.rescates.escalamiento import repetir_cada
from app.seguridad.tokens import EmisorTokens, TokenInvalido

logger = logging.getLogger("app.api.main")  # el mismo de antes: los logs no cambian

# Solo recursos del propio servidor: sin scripts en línea ni de terceros (XSS).
POLITICA_PERMISOS = "geolocation=(self), camera=(self), microphone=(), payment=()"
POLITICA_PWA = ("default-src 'self'; script-src 'self'; style-src 'self'; "
                # #125: blob: son archivos locales del navegador (la tira del video en el panel
                # y la duración del video elegido en la PWA); nunca de otro servidor.
                "img-src 'self' blob:; media-src blob:; "
                "connect-src 'self'; manifest-src 'self'; worker-src 'self'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")

# A-01 (#235): el video, la vista previa y las fotos llegan por partes y tienen su propio tope.
_SUBIDAS_DE_ARCHIVO = re.compile(r"^/(reportes/[^/]+/video|video/trabajos/\d+/vista"
                                 r"|refugio/animales/\d+/foto)$")


def es_subida_de_archivo(ruta: str) -> bool:
    return _SUBIDAS_DE_ARCHIVO.match(ruta) is not None


def ciclo_de_vida(periodicas: list[tuple[Callable[[], object], float | None, str]],
                  motor: Engine | None):
    """Arranca cada tarea periódica con intervalo (None: no se repite, como en las pruebas) y,
    al apagar, las detiene y cierra la base."""
    @asynccontextmanager
    async def ciclo(_app: FastAPI) -> AsyncIterator[None]:
        tareas = [asyncio.create_task(repetir_cada(accion, cada_s, nombre))
                  for accion, cada_s, nombre in periodicas if cada_s]
        yield
        for tarea in tareas:
            tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarea
        if motor is not None:
            motor.dispose()
    return ciclo


def instalar_middlewares(app: FastAPI, repositorio_bitacora: RepositorioBitacora,
                         emisor_tokens: EmisorTokens, token_video: str | None) -> None:
    """Tope del cuerpo (A-01), cabeceras de seguridad (#121) y bitácora (RF-32), en ese orden."""
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
        respuesta = await siguiente(peticion)
        # Prueba de punta a punta (#121, OWASP ZAP): en todas las respuestas, HTTPS por un año
        # (HSTS), el GPS y la cámara solo desde este sitio (la PWA los usa; #212), sin micrófono, y
        # ninguna otra ventana puede manipular esta (COOP).
        respuesta.headers["Strict-Transport-Security"] = "max-age=31536000"
        respuesta.headers["Permissions-Policy"] = POLITICA_PERMISOS
        respuesta.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        if peticion.url.path == "/" or peticion.url.path.startswith(("/app", "/panel",
                                                                  "/inicio", "/diseno")):
            respuesta.headers["Content-Security-Policy"] = POLITICA_PWA
            respuesta.headers["Referrer-Policy"] = "no-referrer"
        return respuesta

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
