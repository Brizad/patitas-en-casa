"""API REST del MVP de Patitas en Casa (FastAPI).

Se inicia con: uvicorn --factory app.api.main:crear_app
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
import mimetypes
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    Request,
)
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine, create_engine
from starlette.concurrency import run_in_threadpool

from app import config
from app.adopciones.fotos import (
    RepositorioFotos,
)
from app.adopciones.repositorio import RepositorioAdopciones
from app.adopciones.servicio import (
    ServicioAdopciones,
)
from app.ajustes import (
    AjustesIp,
    cargar_ajustes,
    cargar_ajustes_correo,
    cargar_ajustes_demo,
    cargar_ajustes_ip,
    cargar_ajustes_seguridad,
)
from app.api.armado import Repositorios, armar_repositorios, armar_video
from app.api.comun import Contexto, ip_del_cliente
from app.api.piloto import crear_rutas_piloto
from app.api.rutas_admin import crear_rutas_admin
from app.api.rutas_adopciones import crear_rutas_adopciones
from app.api.rutas_indicadores import crear_rutas_indicadores
from app.api.rutas_refugio import crear_rutas_refugio
from app.api.rutas_reportes import ReporteEntrada, crear_rutas_reportes
from app.api.rutas_rescates import crear_rutas_rescates
from app.api.rutas_triaje import crear_rutas_triaje
from app.api.seguridad import crear_dependencia_usuario, exigir_rol
from app.api.video import crear_rutas_video
from app.avisos.modelos import AvisoNuevo
from app.avisos.procesador import ProcesadorAvisos
from app.avisos.repositorio import RepositorioAvisos
from app.bd.migraciones import verificar_migraciones
from app.bitacora.repositorio import Evento, RepositorioBitacora
from app.cupos.repositorio import RepositorioCupos
from app.cupos.servicio import Notificador, ServicioCupos
from app.demo import Dependencias, cargar_demo
from app.dominio.modelos import (
    EstadoRescate,
    Prioridad,
    Reporte,
    Rol,
    Usuario,
)
from app.notificaciones.correo import crear_notificador
from app.piloto.servicio import RepositorioPiloto, ServicioPiloto
from app.refugios.repositorio import RepositorioRefugios
from app.reportes.confirmacion import (
    ServicioConfirmacion,
)
from app.reportes.descarte import ServicioDescarte
from app.reportes.repositorio import RepositorioReportes
from app.reportes.servicio import ServicioReportes
from app.rescates.escalamiento import repetir_cada, vigilar_escalamientos
from app.rescates.repositorio import RepositorioRescates
from app.rescates.servicio import (
    ServicioRescates,
)
from app.seguridad.cifrado import PREFIJO_AVISO, CanalConDescifrado, Cifrador
from app.seguridad.tokens import EmisorTokens, TokenInvalido
from app.triaje.combinado import triaje_por_defecto
from app.triaje.servicio import ServicioTriaje
from app.usuarios.intentos import (
    LimiteIntentos,
)
from app.usuarios.repositorio import RepositorioUsuarios
from app.usuarios.servicio import (
    ServicioUsuarios,
)
from app.video.repositorio import RepositorioVideos
from app.video.servicio import ServicioVideo

logger = logging.getLogger(__name__)

# HU-08 (#47): la PWA ciudadana (HTML + JS sencillos) la sirve la misma API en /app/.
CARPETA_PWA = Path(__file__).resolve().parents[1] / "pwa"
# Página de inicio pública (#145): HTML y CSS sin JavaScript, en la raíz del sitio.
CARPETA_INICIO = Path(__file__).resolve().parents[1] / "inicio"
# Sistema de diseño compartido (#164): una hoja de estilo para inicio, PWA y panel.
CARPETA_DISENO = Path(__file__).resolve().parents[1] / "diseno"
# II-03 (#64): panel del personal en React; se compila con «npm run build» en panel/.
CARPETA_PANEL = Path(__file__).resolve().parents[1] / "panel_web"
# Windows puede asociar .js a text/plain en el registro; el navegador exige estos tipos.
for _tipo, _extension in (("text/javascript", ".js"), ("text/css", ".css"),
                          ("application/manifest+json", ".webmanifest"),
                          ("image/svg+xml", ".svg")):
    mimetypes.add_type(_tipo, _extension)
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


# Pueden usar /cola y /refugio/ocupacion. Públicos (RF-01): POST /reportes y
# GET /reportes/{codigo}. POST /refugio/ingresos es solo del coordinador (P-06 del prototipo).
ROLES_PERSONAL = (Rol.VETERINARIO, Rol.COORDINADOR)


def motor_desde_entorno() -> Engine:
    """Conexión a PostgreSQL con la configuración del .env; exige la base migrada (DT-01)."""
    motor = create_engine(cargar_ajustes().url(), pool_pre_ping=True)
    try:
        verificar_migraciones(motor)
    except Exception:
        motor.dispose()
        raise
    return motor


def emisor_desde_entorno() -> EmisorTokens:
    ajustes = cargar_ajustes_seguridad()
    return EmisorTokens(ajustes.jwt_secreto.get_secret_value(), minutos=ajustes.jwt_minutos)


# C901: crear_app es la «raíz de composición»: arma los servicios y los middlewares. Las rutas
# viven en app/api/rutas_*.py (DT-13, #267) y los repositorios en app/api/armado.py (#282).
def crear_app(repositorio: RepositorioReportes | None = None,  # noqa: C901
              repositorio_cupos: RepositorioCupos | None = None, *,
              repositorio_usuarios: RepositorioUsuarios | None = None,
              emisor_tokens: EmisorTokens | None = None,
              notificador: Notificador | None = None,
              limite_intentos: LimiteIntentos | None = None,
              repositorio_rescates: RepositorioRescates | None = None,
              revisar_escalamientos_cada_s: float | None =
              config.REVISION_ESCALAMIENTOS_SEGUNDOS,
              repositorio_avisos: RepositorioAvisos | None = None,
              procesar_avisos_cada_s: float | None = config.REVISION_AVISOS_SEGUNDOS,
              repositorio_refugios: RepositorioRefugios | None = None,
              repositorio_adopciones: RepositorioAdopciones | None = None,
              repositorio_bitacora: RepositorioBitacora | None = None,
              contrasena_demo: str | None = None,
              cifrador: Cifrador | None = None,
              repositorio_fotos: RepositorioFotos | None = None,
              repositorio_videos: RepositorioVideos | None = None,
              repositorio_piloto: RepositorioPiloto | None = None,
              ajustes_ip: AjustesIp | None = None,
              token_video: str | None = None,
              directorio_videos: str | None = None,
              revisar_videos_cada_s: float | None = config.REVISION_VIDEOS_SEGUNDOS) -> FastAPI:
    """Sin argumentos usa PostgreSQL, la clave JWT y el SMTP del .env; las pruebas inyectan
    dobles. Si se inyectan los tres repositorios y no el límite de intentos, los intentos
    fallidos se cuentan en memoria. Mientras la app corre se revisan los rescates sin aceptar
    cada «revisar_escalamientos_cada_s» segundos (None: no se revisan) y se envían los avisos
    pendientes cada «procesar_avisos_cada_s» (#63; None: solo a mano, como en las pruebas)."""
    emisor_tokens = emisor_tokens or emisor_desde_entorno()
    notificador = notificador or crear_notificador(cargar_ajustes_correo())
    # #282: lo inyectado se usa tal cual; lo que falta sale de PostgreSQL (o de memoria).
    dados = Repositorios(**{c: v for c, v in locals().items() if c in Repositorios._fields})
    (repositorio, repositorio_cupos, repositorio_usuarios, limite_intentos, repositorio_rescates,
     repositorio_avisos, repositorio_refugios, cifrador, repositorio_adopciones,
     repositorio_bitacora, repositorio_fotos, repositorio_videos, repositorio_piloto), motor = (
        armar_repositorios(dados, motor_desde_entorno))
    token_video, almacen_videos, almacen_vistas = armar_video(motor, token_video,
                                                           directorio_videos)
    videos = ServicioVideo(
        repositorio_videos, repositorio, almacen_videos, almacen_vistas=almacen_vistas,
        rescate_atendido=lambda codigo: (
            (r := repositorio_rescates.vigente(codigo)) is not None
            and r.estado == EstadoRescate.ATENDIDO))
    usuarios = ServicioUsuarios(repositorio_usuarios)
    adopciones = ServicioAdopciones(repositorio_adopciones)
    dependencia_usuario = crear_dependencia_usuario(repositorio_usuarios, emisor_tokens)
    usuario_actual = Depends(dependencia_usuario)
    # DT-02: el personal se identifica con su token; X-Rol ya no existe.
    personal = exigir_rol(dependencia_usuario, *ROLES_PERSONAL)
    coordinacion = exigir_rol(dependencia_usuario, Rol.COORDINADOR)
    veterinaria = exigir_rol(dependencia_usuario, Rol.VETERINARIO)  # RN-06
    rescatista_actual = exigir_rol(dependencia_usuario, Rol.RESCATISTA)  # HU-06
    administracion = exigir_rol(dependencia_usuario, Rol.ADMINISTRADOR)  # #67
    # #102 / #108: indicadores anonimizados; la Alcaldía solo ve esto (RF-13, RF-31).
    gestion = exigir_rol(dependencia_usuario, Rol.COORDINADOR, Rol.ADMINISTRADOR,
                         Rol.ALCALDIA)
    adoptante_actual = exigir_rol(dependencia_usuario, Rol.ADOPTANTE)  # #85

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
        tareas = []
        if revisar_escalamientos_cada_s:
            # HU-06 (RF-23): rescates sin aceptar a tiempo → aviso al coordinador.
            tareas.append(asyncio.create_task(
                vigilar_escalamientos(rescates.escalar_vencidos, revisar_escalamientos_cada_s)))
        if procesar_avisos_cada_s:
            tareas.append(asyncio.create_task(repetir_cada(
                procesador.procesar, procesar_avisos_cada_s, "envío de avisos pendientes")))
        if revisar_videos_cada_s and token_video:
            tareas.append(asyncio.create_task(repetir_cada(
                videos.revisar, revisar_videos_cada_s, "videos sin analizar a tiempo")))
        yield
        for tarea in tareas:
            tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarea
        if motor is not None:
            motor.dispose()

    app = FastAPI(title="Patitas en Casa", version="1.1.0", lifespan=ciclo_de_vida)
    # Comprime con gzip lo que pase de 1 KB (el JS del panel baja de ~60 KB a ~20 KB): importa
    # en celulares con datos limitados (RNF-07).
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    # #95: reglas + modelo entrenado (el modelo solo sube la prioridad); sin modelo, reglas.
    clasificador, version_triaje = triaje_por_defecto()
    reportes = ServicioReportes(repositorio, ServicioTriaje(clasificador, version=version_triaje))
    rescates = ServicioRescates(repositorio, repositorio_rescates, notificador=notificador,
                                avisos=repositorio_avisos)
    descartes = ServicioDescarte(repositorio)

    def avisos_al_ciudadano(reporte: Reporte, texto: str) -> list[AvisoNuevo]:
        """RF-18: solo si el ciudadano dejó un correo y autorizó el contacto (el contacto solo
        se guarda con la autorización). RN-14: el texto lleva el código y nada más; el
        destinatario va cifrado también en la tabla de avisos."""
        if not reporte.contacto_cifrado or cifrador is None:
            return []
        if "@" not in cifrador.descifrar(reporte.contacto_cifrado):
            return []  # un teléfono se guarda, pero no hay correo al cual avisar
        return [AvisoNuevo(PREFIJO_AVISO + reporte.contacto_cifrado,
                           f"Patitas en Casa: {texto}")]

    def avisar_al_ciudadano(codigo: str, texto: str) -> None:
        """Guarda el aviso en el outbox; el envío es del procesador. Una falla aquí no deshace
        el rescate ni el ingreso, que ya ocurrieron: se registra en el log."""
        try:
            reporte = repositorio.buscar(codigo)
            if reporte is not None:
                repositorio_avisos.agregar(codigo, avisos_al_ciudadano(reporte, texto),
                                           datetime.now(UTC))
        except Exception:
            logger.exception("No se pudo guardar el aviso al ciudadano del reporte %s.", codigo)

    def avisos_al_confirmar(reporte: Reporte, prioridad: Prioridad):
        """Rescatistas de la zona (RF-05) y, si dejó un correo, el ciudadano (RF-18). El
        destinatario del ciudadano va cifrado también en la tabla de avisos."""
        return rescates.avisos_para(reporte, prioridad) + avisos_al_ciudadano(
            reporte, f"un veterinario revisó tu reporte {reporte.codigo}. "
            "Consulta cómo sigue con tu código en la página de seguimiento.")

    confirmaciones = ServicioConfirmacion(repositorio, planificar_avisos=avisos_al_confirmar)
    procesador = ProcesadorAvisos(repositorio_avisos, CanalConDescifrado(notificador, cifrador))
    app.state.procesador_avisos = procesador  # las pruebas lo ejecutan a mano
    app.state.bitacora = repositorio_bitacora
    app.state.usuarios = repositorio_usuarios  # las pruebas agregan cuentas
    # #109: datos de demostración. Con PostgreSQL se leen del entorno (Render no tiene
    # consola); las pruebas pasan la contraseña. Un error aquí no impide que la API arranque.
    if motor is not None:
        contrasena_demo = contrasena_demo or cargar_ajustes_demo().contrasena_si_activa()
    servicios_demo = (reportes, confirmaciones, rescates, repositorio_cupos,
                      repositorio_adopciones)
    app.state.demo_servicios = servicios_demo
    if contrasena_demo:
        try:
            cargar_demo(Dependencias(repositorio_usuarios, *servicios_demo), contrasena_demo)
        except Exception:
            logger.exception("No se pudieron cargar los datos de demostración.")

    def cupos_de(usuario: Usuario) -> ServicioCupos:
        """#75: los cupos del refugio de la persona; sin vínculo, el primer refugio (como
        antes de RF-14). Así dos coordinadores de refugios distintos no se mezclan."""
        if usuario.refugio_id is None:
            return ServicioCupos(repositorio_cupos, notificador)
        # RF-07: la alerta del 90 % va a los coordinadores activos de ESE refugio.
        coordinadores = [u.correo for u in repositorio_usuarios.todos()
                         if u.rol == Rol.COORDINADOR and u.activo
                         and u.refugio_id == usuario.refugio_id]
        return ServicioCupos(repositorio_cupos.para_refugio(usuario.refugio_id), notificador,
                             coordinadores)

    def fichas_de(usuario: Usuario) -> RepositorioCupos:
        return (repositorio_cupos if usuario.refugio_id is None
                else repositorio_cupos.para_refugio(usuario.refugio_id))

    # A-04 / DT-11 (#278): de dónde sale la IP del cliente; sin ajustes, como siempre.
    if ajustes_ip is None:
        ajustes_ip = cargar_ajustes_ip() if motor is not None else AjustesIp()

    def ip_de(peticion: Request) -> str:
        return ip_del_cliente(peticion, ajustes_ip)

    # DT-13 (#267): lo armado hasta aquí, para los routers de cada módulo (app/api/rutas_*.py).
    ctx = Contexto(**{nombre: valor for nombre, valor in locals().items()
                      if not nombre.startswith("_")})

    app.include_router(crear_rutas_admin(ctx))  # DT-13 (#267)

    app.include_router(crear_rutas_adopciones(ctx))  # DT-13 (#267)

    app.include_router(crear_rutas_reportes(ctx))  # DT-13 (#267)

    app.include_router(crear_rutas_triaje(ctx))  # DT-13 (#267)

    app.include_router(crear_rutas_rescates(ctx))  # DT-13 (#267)

    app.include_router(crear_rutas_refugio(ctx))  # DT-13 (#267)

    # --- HU-08: PWA ciudadana (#59) --------------------------------------------------

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

    app.include_router(crear_rutas_indicadores(ctx))  # DT-13 (#267)

    @app.get("/", include_in_schema=False)
    def inicio():
        return FileResponse(CARPETA_INICIO / "index.html", media_type="text/html")

    app.include_router(crear_rutas_piloto(ServicioPiloto(repositorio_piloto), administracion,
                                          ReporteEntrada))  # RNF-06 (#258)
    app.include_router(crear_rutas_video(videos, almacen_videos, token_video, personal,
                                          almacen_vistas))
    app.mount("/app", StaticFiles(directory=CARPETA_PWA, html=True), name="pwa")
    app.mount("/inicio", StaticFiles(directory=CARPETA_INICIO), name="inicio")
    app.mount("/diseno", StaticFiles(directory=CARPETA_DISENO), name="diseno")
    if (CARPETA_PANEL / "index.html").exists():  # sin compilar, /panel no existe
        app.mount("/panel", StaticFiles(directory=CARPETA_PANEL, html=True), name="panel")

    return app
