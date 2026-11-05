"""API REST del MVP de Patitas en Casa (FastAPI).

Se inicia con: uvicorn --factory app.api.main:crear_app
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
import math
import mimetypes
import re
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Engine, create_engine
from starlette.concurrency import run_in_threadpool

from app import config
from app.adopciones.asignacion import asignar
from app.adopciones.compatibilidad import calcular
from app.adopciones.compromiso import lineas_compromiso
from app.adopciones.fotos import (
    RepositorioFotos,
    RepositorioFotosEnMemoria,
)
from app.adopciones.fotos_postgres import RepositorioFotosPostgres
from app.adopciones.modelos import (
    EstadoSolicitud,
    Seguimiento,
)
from app.adopciones.repositorio import RepositorioAdopciones, RepositorioAdopcionesEnMemoria
from app.adopciones.repositorio_postgres import RepositorioAdopcionesPostgres
from app.adopciones.servicio import (
    RazonInvalida,
    RestriccionDura,
    SeguimientoNoValido,
    ServicioAdopciones,
    SinCupoParaDevolucion,
    SolicitudNoEncontrada,
    SolicitudYaDecidida,
)
from app.ajustes import (
    cargar_ajustes,
    cargar_ajustes_admin,
    cargar_ajustes_correo,
    cargar_ajustes_datos,
    cargar_ajustes_demo,
    cargar_ajustes_seguridad,
    cargar_ajustes_video,
)
from app.api.comun import Contexto, fecha_utc
from app.api.comun import cambiar as _cambio
from app.api.piloto import crear_rutas_piloto
from app.api.rutas_admin import crear_rutas_admin
from app.api.rutas_adopciones import _compatibilidad, crear_rutas_adopciones
from app.api.rutas_indicadores import crear_rutas_indicadores
from app.api.seguridad import crear_dependencia_usuario, exigir_rol
from app.api.video import crear_rutas_video
from app.avisos.modelos import AvisoNuevo
from app.avisos.procesador import ProcesadorAvisos
from app.avisos.repositorio import RepositorioAvisos, RepositorioAvisosEnMemoria, resumen
from app.avisos.repositorio_postgres import RepositorioAvisosPostgres
from app.bd.esquema import vistas_trozos
from app.bd.migraciones import verificar_migraciones
from app.bitacora.repositorio import Evento, RepositorioBitacora, RepositorioBitacoraEnMemoria
from app.bitacora.repositorio_postgres import RepositorioBitacoraPostgres
from app.cupos.fichas import AnimalNoEncontrado, NotaInvalida, ServicioFichas
from app.cupos.repositorio import RepositorioCupos
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.cupos.servicio import CupoAgotado, Notificador, ServicioCupos
from app.demo import Dependencias, cargar_demo
from app.documentos.pdf import generar_pdf
from app.dominio.modelos import (
    Animal,
    Especie,
    EstadoReporte,
    EstadoRescate,
    MotivoDescarte,
    MotivoEgreso,
    Prioridad,
    Refugio,
    Reporte,
    Rescate,
    ResultadoRescate,
    Rol,
    TipoNota,
    Ubicacion,
    Usuario,
)
from app.notificaciones.correo import crear_notificador
from app.piloto.repositorio_postgres import RepositorioPilotoPostgres
from app.piloto.servicio import RepositorioPiloto, RepositorioPilotoEnMemoria, ServicioPiloto
from app.refugios.repositorio import RepositorioRefugios, RepositorioRefugiosEnMemoria
from app.refugios.repositorio_postgres import RepositorioRefugiosPostgres
from app.reportes.confirmacion import (
    AjusteSinJustificacion,
    ReporteNoEncontrado,
    ReporteYaConfirmado,
    ServicioConfirmacion,
)
from app.reportes.descarte import DescarteInvalido, ServicioDescarte
from app.reportes.duplicados import posibles_duplicados
from app.reportes.repositorio import RepositorioReportes
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.reportes.seguimiento import linea_de_tiempo, normalizar_codigo
from app.reportes.servicio import ReporteInvalido, ServicioReportes
from app.rescates.escalamiento import repetir_cada, vigilar_escalamientos
from app.rescates.repositorio import RepositorioRescates, RepositorioRescatesEnMemoria
from app.rescates.repositorio_postgres import RepositorioRescatesPostgres
from app.rescates.servicio import (
    PRIORIDADES_DE_RESCATE,
    PasoInvalido,
    RescateNoOfrecido,
    ServicioRescates,
)
from app.seguridad.cifrado import PREFIJO_AVISO, CanalConDescifrado, Cifrador
from app.seguridad.tokens import EmisorTokens, TokenInvalido
from app.triaje.combinado import triaje_por_defecto
from app.triaje.servicio import ServicioTriaje, ordenar_cola
from app.usuarios.admin_inicial import crear_admin_inicial
from app.usuarios.intentos import (
    LimiteIntentos,
    RepositorioIntentosEnMemoria,
    clave_reporte,
)
from app.usuarios.intentos_postgres import RepositorioIntentosPostgres
from app.usuarios.repositorio import RepositorioUsuarios
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import (
    PATRON_CORREO,
    ServicioUsuarios,
)
from app.video.almacen import AlmacenEnDisco, AlmacenEnPostgres
from app.video.repositorio import RepositorioVideos, RepositorioVideosEnMemoria
from app.video.repositorio_postgres import RepositorioVideosPostgres
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


class ReporteEntrada(BaseModel):
    descripcion: str = Field(max_length=config.MAX_CARACTERES_DESCRIPCION)  # A-01 (#235)
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = Field(default=None, max_length=config.MAX_CARACTERES_DIRECCION)
    video_segundos: int | None = Field(default=None, ge=0)
    video_mb: float | None = Field(default=None, ge=0)
    comuna: int | None = Field(default=None, ge=1, le=10)  # HU-06: comunas de Cúcuta
    # RF-18 (#111): opcional y con autorización expresa; se guarda cifrado (RNF-08).
    contacto: str | None = Field(default=None, max_length=120)
    autoriza_contacto: bool = False


PATRON_TELEFONO = re.compile(r"^\+?\d{7,15}$")


def normalizar_contacto(contacto: str) -> str:
    """Correo en minúsculas o teléfono solo con dígitos (y «+»); si no es ninguno, error."""
    contacto = contacto.strip()
    if PATRON_CORREO.match(contacto.lower()):
        return contacto.lower()
    telefono = re.sub(r"[\s()-]", "", contacto)
    if PATRON_TELEFONO.match(telefono):
        return telefono
    raise ValueError("El contacto debe ser un correo o un teléfono.")


Comuna = Annotated[int, Field(ge=1, le=10)]
# RF-12 (#61): la PWA la genera al crear el reporte (32 caracteres hex) y la repite al reenviar.
ClaveIdempotencia = Annotated[str | None, Header(alias="Idempotency-Key", min_length=16,
                                                 max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class ZonaEntrada(BaseModel):
    """Comunas que cubre el rescatista; lista vacía = toda la ciudad (#46)."""

    comunas: list[Comuna] = Field(max_length=10)


class ConfirmacionEntrada(BaseModel):
    """Sin prioridad se confirma la sugerida; con otra distinta, la justificación es
    obligatoria (RN-16)."""

    prioridad: Prioridad | None = None
    justificacion: str | None = Field(default=None, max_length=1000)


class DescarteEntrada(BaseModel):
    """D-02: falso o duplicado (con el código del original, opcional)."""

    motivo: MotivoDescarte
    justificacion: str | None = Field(default=None, max_length=1000)
    duplicado_de: str | None = Field(default=None, max_length=8)


class DisponibilidadEntrada(BaseModel):
    disponible: bool


class ResultadoEntrada(BaseModel):
    resultado: ResultadoRescate


def _rescate(rescate: Rescate, reporte: Reporte | None = None) -> dict:
    datos = {"codigo": rescate.codigo, "estado": rescate.estado.value}
    if reporte is not None:
        # La ubicación exacta solo la ve quien aceptó el rescate.
        datos["prioridad"] = reporte.prioridad.value
        datos["descripcion"] = reporte.descripcion
        datos["ubicacion"] = {"latitud": reporte.ubicacion.latitud,
                              "longitud": reporte.ubicacion.longitud,
                              "direccion": reporte.ubicacion.direccion,
                              "comuna": reporte.ubicacion.comuna}
    return datos


class IngresoEntrada(BaseModel):
    reporte: str | None = None  # si viene, el ciudadano que lo reportó recibe un aviso
    nombre: str
    especie: Especie
    estado_salud: str
    vacunado: bool = False
    esterilizado: bool = False


class EgresoEntrada(BaseModel):
    motivo: MotivoEgreso


class NotaSolicitudEntrada(BaseModel):
    texto: str = Field(max_length=1000)  # nota de la visita o motivo de la devolución


class DecisionEntrada(BaseModel):
    aprobar: bool
    razon: str | None = Field(default=None, max_length=1000)  # obligatoria al rechazar


class SeguimientoEntrada(BaseModel):
    nota: str = Field(max_length=2000)


def _seguimiento(x: Seguimiento, ahora: datetime) -> dict:
    return {"id": x.id, "dia": x.dia, "programado_para": fecha_utc(x.programado_para),
            "realizado_en": fecha_utc(x.realizado_en), "nota": x.nota,
            "registrado_por": x.registrado_por,
            # Vencido: ya pasó la fecha y nadie lo registró (aparece primero en la lista).
            "vencido": x.realizado_en is None and x.programado_para < ahora}


class NotaEntrada(BaseModel):
    tipo: TipoNota
    texto: str = Field(max_length=2000)


def _ficha(animal: Animal) -> dict:
    return {"id": animal.id, "nombre": animal.nombre, "especie": animal.especie.value,
            "estado_salud": animal.estado_salud, "vacunado": animal.vacunado,
            "esterilizado": animal.esterilizado, "ingresado_en": fecha_utc(animal.ingresado_en),
            "egresado_en": fecha_utc(animal.egresado_en),
            "motivo_egreso": animal.motivo_egreso.value if animal.motivo_egreso else None}


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


# C901: mccabe suma aquí las ~70 funciones de endpoint anidadas; cada una por separado es
# sencilla. crear_app es la «raíz de composición» que conecta adaptadores y rutas.
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
    motor = None
    if repositorio is None or repositorio_cupos is None or repositorio_usuarios is None:
        motor = motor_desde_entorno()
        repositorio = repositorio or RepositorioPostgres(motor)
        repositorio_cupos = repositorio_cupos or RepositorioCuposPostgres.primer_refugio(motor)
        repositorio_usuarios = repositorio_usuarios or RepositorioUsuariosPostgres(motor)
        # #67: en Render no hay consola; la primera cuenta de administración sale del entorno.
        crear_admin_inicial(repositorio_usuarios, cargar_ajustes_admin())
    # DT-06: con PostgreSQL el límite vale para todos los procesos y sobrevive a un reinicio.
    limite_intentos = limite_intentos or LimiteIntentos(
        RepositorioIntentosPostgres(motor) if motor is not None
        else RepositorioIntentosEnMemoria())
    repositorio_rescates = repositorio_rescates or (
        RepositorioRescatesPostgres(motor) if motor is not None
        else RepositorioRescatesEnMemoria())
    # #63: los avisos viven en la misma base que los reportes (la confirmación los guarda).
    repositorio_avisos = repositorio_avisos or (
        RepositorioAvisosPostgres(motor) if motor is not None
        else getattr(repositorio, "avisos", None) or RepositorioAvisosEnMemoria())
    # #67 (RF-14): en memoria arranca con el refugio de los cupos (id 1), como la migración 0002.
    if repositorio_refugios is None:
        if motor is not None:
            repositorio_refugios = RepositorioRefugiosPostgres(motor)
        else:
            demo = repositorio_cupos.refugio()
            repositorio_refugios = RepositorioRefugiosEnMemoria(
                [Refugio(demo.nombre, demo.capacidad, demo.ocupados, id=1)])
    if cifrador is None and motor is not None:
        clave_datos = cargar_ajustes_datos().clave_datos
        cifrador = Cifrador(clave_datos.get_secret_value()) if clave_datos else None
    if repositorio_adopciones is None and motor is not None:
        # RNF-08 (#149): perfiles cifrados; los que estaban en claro se cifran al arrancar.
        repositorio_adopciones = RepositorioAdopcionesPostgres(motor, cifrador)
        cifrados = repositorio_adopciones.cifrar_perfiles_en_claro()
        if cifrados:
            logger.info("Perfiles de adoptante cifrados al arrancar: %d.", cifrados)
    repositorio_adopciones = repositorio_adopciones or RepositorioAdopcionesEnMemoria(
        repositorio_cupos)
    repositorio_bitacora = repositorio_bitacora or (
        RepositorioBitacoraPostgres(motor) if motor is not None
        else RepositorioBitacoraEnMemoria())
    repositorio_fotos = repositorio_fotos or (
        RepositorioFotosPostgres(motor) if motor is not None else RepositorioFotosEnMemoria())
    # #125: análisis de video con el trabajador local. Sin token, apagado (manda el texto).
    repositorio_videos = repositorio_videos or (
        RepositorioVideosPostgres(motor) if motor is not None else RepositorioVideosEnMemoria())
    if motor is not None:
        ajustes_video = cargar_ajustes_video()
        token_video = token_video or (ajustes_video.video_token.get_secret_value()
                                      if ajustes_video.video_token else None)
        directorio_videos = directorio_videos or ajustes_video.video_dir
    maximo_vista = config.VISTA_VIDEO_MAX_MB * 1024 * 1024
    if motor is not None and not directorio_videos:
        almacen_videos = AlmacenEnPostgres(motor)  # #188: sobrevive al reinicio de Render
        almacen_vistas = AlmacenEnPostgres(motor, vistas_trozos, maximo_vista)  # #214
    else:  # sin base (pruebas) o con VIDEO_DIR explícito: disco
        carpeta_videos = directorio_videos or Path(tempfile.gettempdir()) / "patitas-videos"
        almacen_videos = AlmacenEnDisco(carpeta_videos)
        almacen_vistas = AlmacenEnDisco(carpeta_videos, maximo_vista, ".vista")
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

    # DT-13 (#267): lo armado hasta aquí, para los routers de cada módulo (app/api/rutas_*.py).
    ctx = Contexto(**{nombre: valor for nombre, valor in locals().items()
                      if not nombre.startswith("_")})

    app.include_router(crear_rutas_admin(ctx))  # DT-13 (#267)

    app.include_router(crear_rutas_adopciones(ctx))  # DT-13 (#267)

    @app.get("/refugio/solicitudes")
    def solicitudes_del_refugio(coordinador: Usuario = coordinacion):
        """Las solicitudes por animales de SU refugio, con el perfil del adoptante: es lo que
        el coordinador necesita para decidir (y nada más: ni contraseña ni otros datos)."""
        animales = fichas_de(coordinador)
        respuesta = []
        for s in repositorio_adopciones.solicitudes():
            animal = animales.animal(s.animal_id)
            if animal is None:
                continue
            perfil = repositorio_adopciones.perfil(s.adoptante)
            respuesta.append({
                "id": s.id, "animal_id": s.animal_id, "animal": animal.nombre,
                "adoptante": s.adoptante, "mensaje": s.mensaje, "estado": s.estado.value,
                "razon": s.razon,
                "creada_en": fecha_utc(s.creada_en),
                "perfil": None if perfil is None else {
                    k: v for k, v in vars(perfil).items()
                    if k not in ("correo", "actualizado_en")},
                # RF-09: ayuda a decidir; la decisión sigue siendo del coordinador (RN-16).
                "compatibilidad": None if perfil is None else _compatibilidad(
                    calcular(perfil, repositorio_adopciones.publicacion(s.animal_id)))})
        return respuesta

    @app.get("/refugio/jornada/propuesta")
    def propuesta_de_jornada(coordinador: Usuario = coordinacion):
        """RF-28: con los adoptantes que tienen solicitudes pendientes en su refugio y los
        animales disponibles de su refugio, la combinación que maximiza la compatibilidad
        total. Es una propuesta: no aprueba nada (RN-16)."""
        animales = fichas_de(coordinador)
        disponibles = [a for a in repositorio_adopciones.disponibles()
                       if animales.animal(a.animal_id) is not None]
        pendientes = [s for s in repositorio_adopciones.solicitudes()
                      if s.estado == EstadoSolicitud.PENDIENTE
                      and animales.animal(s.animal_id) is not None]
        adoptantes = list(dict.fromkeys(s.adoptante for s in pendientes))
        perfiles = [repositorio_adopciones.perfil(c) for c in adoptantes]
        if not disponibles or not adoptantes:
            return []
        tabla = [[calcular(p, a) for a in disponibles] for p in perfiles]
        pidio = {(s.adoptante, s.animal_id) for s in pendientes}
        return [{"adoptante": adoptantes[i], "animal_id": disponibles[j].animal_id,
                 "animal": disponibles[j].nombre, **_compatibilidad(tabla[i][j]),
                 "solicito_este_animal": (adoptantes[i], disponibles[j].animal_id) in pidio}
                for i, j in asignar([[c.puntaje for c in fila] for fila in tabla])]

    @app.post("/refugio/solicitudes/{solicitud_id}/decision")
    def decidir_solicitud(solicitud_id: int, datos: DecisionEntrada, peticion: Request,
                          coordinador: Usuario = coordinacion):
        """RF-27: aprobar (RN-05, RN-11; egreso por adopción y seguimientos RF-10) o
        rechazar con razón. Solo solicitudes de animales de su refugio."""
        solicitud = repositorio_adopciones.solicitud(solicitud_id)
        if solicitud is None or fichas_de(coordinador).animal(solicitud.animal_id) is None:
            raise HTTPException(status_code=404, detail="No hay esa solicitud en tu refugio.")
        try:
            s = adopciones.decidir(coordinador, solicitud_id, datos.aprobar, datos.razon)
            _cambio(peticion, {"estado": solicitud.estado.value}, {"estado": s.estado.value})
        except SolicitudNoEncontrada as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (SolicitudYaDecidida, RestriccionDura) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RazonInvalida as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": s.id, "estado": s.estado.value, "razon": s.razon,
                "seguimientos": [{"dia": x.dia, "programado_para": fecha_utc(x.programado_para)}
                                 for x in repositorio_adopciones.seguimientos(solicitud_id)]}

    def _solicitud_del_refugio(solicitud_id: int, coordinador: Usuario) -> None:
        s = repositorio_adopciones.solicitud(solicitud_id)
        if s is None or fichas_de(coordinador).animal(s.animal_id) is None:
            raise HTTPException(status_code=404, detail="No hay esa solicitud en tu refugio.")

    @app.post("/refugio/solicitudes/{solicitud_id}/visita")
    def pedir_visita(solicitud_id: int, datos: NotaSolicitudEntrada,
                     coordinador: Usuario = coordinacion):
        """RF-27: pedir una visita previa antes de aprobar o rechazar."""
        _solicitud_del_refugio(solicitud_id, coordinador)
        try:
            s = adopciones.pedir_visita(coordinador, solicitud_id, datos.texto)
        except SolicitudYaDecidida as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RazonInvalida as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": s.id, "estado": s.estado.value, "nota": s.razon}

    @app.post("/refugio/solicitudes/{solicitud_id}/devolucion")
    def registrar_devolucion(solicitud_id: int, datos: NotaSolicitudEntrada,
                             coordinador: Usuario = coordinacion):
        """RF-10, RN-13: devolución con su motivo; el animal reingresa y vuelve al catálogo."""
        _solicitud_del_refugio(solicitud_id, coordinador)
        try:
            s = adopciones.devolver(coordinador, solicitud_id, datos.texto)
        except (SolicitudYaDecidida, SinCupoParaDevolucion) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RazonInvalida as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": s.id, "estado": s.estado.value, "motivo": s.razon}

    @app.get("/refugio/seguimientos")
    def seguimientos_del_refugio(coordinador: Usuario = coordinacion):
        """RF-10: seguimientos de las adopciones de animales de su refugio, los pendientes
        primero y por fecha."""
        animales = fichas_de(coordinador)
        ahora = datetime.now(UTC)
        filas = []
        for s in repositorio_adopciones.solicitudes():
            animal = animales.animal(s.animal_id)
            if s.estado != EstadoSolicitud.APROBADA or animal is None:
                continue
            for x in repositorio_adopciones.seguimientos(s.id):
                filas.append({**_seguimiento(x, ahora), "solicitud_id": s.id,
                              "animal": animal.nombre, "adoptante": s.adoptante})
        return sorted(filas, key=lambda f: (f["realizado_en"] is not None,
                                            f["programado_para"]))

    @app.post("/refugio/seguimientos/{seguimiento_id}")
    def registrar_seguimiento(seguimiento_id: int, datos: SeguimientoEntrada,
                              coordinador: Usuario = coordinacion):
        mios = {f["id"] for f in seguimientos_del_refugio(coordinador)}
        if seguimiento_id not in mios:
            raise HTTPException(status_code=404, detail="No hay ese seguimiento en tu refugio.")
        try:
            hecho = adopciones.registrar_seguimiento(coordinador, seguimiento_id, datos.nota)
        except SeguimientoNoValido as error:
            raise HTTPException(status_code=409 if "registrado" in str(error) else 422,
                                detail=str(error)) from error
        return _seguimiento(hecho, datetime.now(UTC))

    acceso_adopcion = exigir_rol(dependencia_usuario, Rol.ADOPTANTE, Rol.COORDINADOR)

    @app.get("/adopciones/solicitudes/{solicitud_id}/compromiso.pdf")
    def compromiso_de_adopcion(solicitud_id: int, usuario: Usuario = acceso_adopcion):
        """RF-29: el adoptante de la solicitud o el coordinador del refugio del animal; para
        cualquier otro la solicitud «no existe» (404), así no se adivinan solicitudes ajenas."""
        s = repositorio_adopciones.solicitud(solicitud_id)
        if s is None or (s.adoptante != usuario.correo if usuario.rol == Rol.ADOPTANTE
                         else fichas_de(usuario).animal(s.animal_id) is None):
            raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
        if s.estado != EstadoSolicitud.APROBADA:
            raise HTTPException(status_code=409,
                                detail="El compromiso existe solo para adopciones aprobadas.")
        adoptante = repositorio_usuarios.buscar_por_correo(s.adoptante)
        pdf = generar_pdf(lineas_compromiso(
            s, repositorio_adopciones.publicacion(s.animal_id),
            adoptante.nombre if adoptante else s.adoptante,
            repositorio_adopciones.seguimientos(s.id),
            repositorio_refugios.de_animal(s.animal_id)))
        return Response(pdf, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="compromiso-{s.id}.pdf"'})

    def contar_reporte(peticion: Request) -> None:
        """A-02 (#237): 429 con Retry-After si esta IP ya mandó el máximo de reportes."""
        limite = [clave_reporte(peticion.client.host if peticion.client else "desconocida")]
        espera = limite_intentos.segundos_de_bloqueo(limite)
        if espera:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Recibimos muchos reportes desde esta conexión. Si es una emergencia, "
                       f"intenta de nuevo en {math.ceil(espera / 60)} minutos.",
                headers={"Retry-After": str(espera)})
        limite_intentos.registrar_fallo(limite)

    @app.post("/reportes", status_code=201)
    def crear_reporte(datos: ReporteEntrada, respuesta: Response, peticion: Request,
                      clave: ClaveIdempotencia = None):
        """RF-01. RF-12 (#61): con Idempotency-Key, reenviar el mismo reporte devuelve el mismo
        código con 200 en vez de crear otro; sin el encabezado funciona como antes.
        A-02 (#237): máximo REPORTES_MAXIMOS_POR_IP reportes nuevos por IP en la ventana."""
        if clave is None or repositorio.buscar_por_clave(clave) is None:  # reenvío: no cuenta
            contar_reporte(peticion)
        ubicacion = Ubicacion(datos.latitud, datos.longitud, datos.direccion, datos.comuna)
        video = (datos.video_segundos, datos.video_mb)
        contacto = None
        if datos.contacto and datos.contacto.strip():
            if not datos.autoriza_contacto:
                raise HTTPException(status_code=422, detail=(
                    "Para guardar tu contacto debes autorizar que lo usemos solo para avisarte "
                    "sobre este reporte (Ley 1581 de 2012)."))
            if cifrador is None:
                raise HTTPException(status_code=422, detail="Por ahora no podemos guardar "
                                    "contactos; tu reporte se puede enviar sin él.")
            try:
                contacto = cifrador.cifrar(normalizar_contacto(datos.contacto))
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        try:
            if clave is None:
                r = reportes.registrar(datos.descripcion, ubicacion, *video)
            else:
                r, nuevo = reportes.registrar_una_vez(clave, datos.descripcion, ubicacion, *video)
                if not nuevo:
                    respuesta.status_code = status.HTTP_200_OK
        except ReporteInvalido as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if contacto and r.contacto_cifrado is None:
            r.contacto_cifrado = contacto
            repositorio.guardar(r)
        return {"codigo": r.codigo, "estado": r.estado.value}

    @app.get("/reportes/{codigo}")
    def estado_reporte(codigo: str):
        r = repositorio.buscar(normalizar_codigo(codigo))
        if r is None:
            raise HTTPException(status_code=404, detail="Código de seguimiento no encontrado.")
        return {"codigo": r.codigo, "estado": r.estado.value}

    @app.get("/reportes/{codigo}/seguimiento")
    def seguimiento_del_reporte(codigo: str):
        """HU-08 (público): línea de tiempo sin datos personales (RN-14)."""
        codigo = normalizar_codigo(codigo)
        reporte = repositorio.buscar(codigo)
        if reporte is None:
            raise HTTPException(status_code=404, detail="Código de seguimiento no encontrado.")
        decisiones = repositorio.decisiones(codigo)
        descarte = repositorio.descarte(codigo)
        pasos, ultimo_cambio = linea_de_tiempo(
            reporte, decisiones[-1] if decisiones else None, repositorio_rescates.vigente(codigo),
            descarte.descartado_en if descarte else None)
        return {"codigo": codigo, "ultimo_cambio": fecha_utc(ultimo_cambio),
                "pasos": [{"nombre": p.nombre, "estado": p.estado, "detalle": p.detalle,
                           "fecha": fecha_utc(p.fecha)} for p in pasos]}

    @app.get("/cola", dependencies=[personal])
    def cola():
        """Reportes pendientes de confirmar (HU-02); los confirmados salen de la cola."""
        pendientes = repositorio.pendientes()  # A-03 (#239): no toda la historia
        # RF-17: un duplicado está a 2 horas o menos; basta con lo creado desde entonces.
        todos = repositorio.creados_desde(
            min(r.creado_en for r in pendientes) - timedelta(hours=config.DUPLICADO_HORAS)
        ) if pendientes else []
        return [
            {"codigo": r.codigo, "prioridad": r.prioridad.value, "estado": r.estado.value,
             "confianza": r.confianza, "evidencias": r.evidencias,
             "version_modelo": r.version_modelo,
             # Detalle para decidir de un vistazo: qué pasó, dónde y cuándo. Nunca el contacto.
             "descripcion": r.descripcion, "creado_en": fecha_utc(r.creado_en),
             "video_segundos": r.video_segundos,
             "ubicacion": {"latitud": r.ubicacion.latitud, "longitud": r.ubicacion.longitud,
                           "direccion": r.ubicacion.direccion, "comuna": r.ubicacion.comuna},
             # RF-17: se compara también con los ya confirmados (el original suele estarlo).
             "posibles_duplicados": posibles_duplicados(r, todos)}
            for r in ordenar_cola(pendientes)
        ]

    @app.post("/reportes/{codigo}/confirmacion")
    def confirmar_prioridad(codigo: str, datos: ConfirmacionEntrada, peticion: Request,
                            veterinario: Usuario = veterinaria):
        """HU-02: el veterinario confirma la prioridad sugerida o la ajusta con justificación.

        #63 (outbox): si queda crítica o alta, los avisos a los rescatistas de la zona se
        guardan como pendientes en la misma transacción y el procesador los envía después.
        La respuesta dice que el aviso está pendiente, nunca que llegó (D-05)."""
        try:
            resultado = confirmaciones.confirmar_y_programar(
                codigo.upper(), veterinario, datos.prioridad, datos.justificacion)
        except ReporteNoEncontrado as error:
            raise HTTPException(status_code=404, detail="Reporte no encontrado.") from error
        except ReporteYaConfirmado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except AjusteSinJustificacion as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        decision = resultado.decision
        _cambio(peticion, {"prioridad": decision.prioridad_sugerida.value},
                {"prioridad": decision.prioridad_final.value,
                 "estado": EstadoReporte.CONFIRMADO.value})
        if decision.prioridad_final not in PRIORIDADES_DE_RESCATE:
            estado_aviso = "no_aplica"  # media y baja las programa el refugio
        else:
            estado_aviso = "pendiente" if resultado.avisos else "sin_destinatarios"
        return {"codigo": decision.codigo, "estado": EstadoReporte.CONFIRMADO.value,
                "prioridad": decision.prioridad_final.value, "ajustada": decision.ajustada,
                "avisos": {"programados": resultado.avisos, "estado": estado_aviso}}

    @app.post("/reportes/{codigo}/descarte")
    def descartar_reporte(codigo: str, datos: DescarteEntrada, peticion: Request,
                          veterinario: Usuario = veterinaria):
        """D-02: falso o duplicado. Como confirmar, sale de la cola y es una sola vez (409)."""
        antes = repositorio.buscar(codigo.upper())
        original = datos.duplicado_de.upper() if datos.duplicado_de else None
        try:
            descartes.descartar(codigo.upper(), veterinario, datos.motivo, datos.justificacion,
                                duplicado_de=original)
        except ReporteNoEncontrado as error:
            raise HTTPException(status_code=404, detail="Reporte no encontrado.") from error
        except ReporteYaConfirmado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except DescarteInvalido as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        _cambio(peticion, {"estado": antes.estado.value},
                {"estado": EstadoReporte.DESCARTADO.value, "motivo": datos.motivo.value})
        return {"codigo": codigo.upper(), "estado": EstadoReporte.DESCARTADO.value}

    @app.get("/reportes/{codigo}/avisos", dependencies=[personal])
    def avisos_del_reporte(codigo: str):
        """#63: estado real de los avisos de un reporte (pendiente, enviado, fallido…)."""
        codigo = codigo.upper()
        avisos = repositorio_avisos.de_reporte(codigo)
        return {"codigo": codigo, "resumen": resumen(avisos),
                "avisos": [{"destinatario": a.destinatario, "estado": a.estado.value,
                            "intentos": a.intentos, "ultimo_error": a.ultimo_error}
                           for a in avisos]}

    @app.get("/reportes/{codigo}/decisiones", dependencies=[personal])
    def bitacora_de_triaje(codigo: str):
        return [{"veterinario": d.veterinario, "prioridad_sugerida": d.prioridad_sugerida.value,
                 "prioridad_final": d.prioridad_final.value, "justificacion": d.justificacion,
                 "decidido_en": fecha_utc(d.decidido_en), "version_modelo": d.version_modelo}
                for d in repositorio.decisiones(codigo.upper())]

    @app.get("/veterinario/historial")
    def historial_del_veterinario(veterinario: Usuario = veterinaria):
        """Lo que este veterinario confirmó, ajustó o descartó, del más reciente al más viejo.
        Sale de la bitácora `decisiones_triaje` y de los descartes (D-02)."""
        decisiones = repositorio.decisiones_de(veterinario.correo)
        descartes = repositorio.descartes_de(veterinario.correo)
        # DT-12 (#265): todos los reportes en una consulta, no uno por fila.
        reportes_ = repositorio.buscar_varios([x.codigo for x in [*decisiones, *descartes]])
        filas = []
        for d in decisiones:
            ajustada = d.prioridad_final != d.prioridad_sugerida
            filas.append((d.decidido_en, {
                "codigo": d.codigo, "accion": "ajustado" if ajustada else "confirmado",
                "prioridad_sugerida": d.prioridad_sugerida.value,
                "prioridad_final": d.prioridad_final.value, "justificacion": d.justificacion}))
        for x in descartes:
            reporte = reportes_.get(x.codigo)
            sugerida = reporte.prioridad if reporte else None
            filas.append((x.descartado_en, {
                "codigo": x.codigo, "accion": "descartado",
                "prioridad_sugerida": sugerida.value if sugerida else None,
                "prioridad_final": None, "justificacion": x.justificacion}))
        resultado = []
        for fecha, fila in sorted(filas, key=lambda f: f[0], reverse=True):
            reporte = reportes_.get(fila["codigo"])
            resultado.append({**fila, "fecha": fecha_utc(fecha),
                              "estado": reporte.estado.value if reporte else None})
        return resultado

    # --- HU-06: rescatistas (RF-05, RF-15, RN-08) --------------------------------------

    @app.put("/rescatistas/yo/disponibilidad")
    def cambiar_disponibilidad(datos: DisponibilidadEntrada,
                               rescatista: Usuario = rescatista_actual):
        rescates.cambiar_disponibilidad(rescatista, datos.disponible)
        return {"disponible": datos.disponible}

    @app.put("/rescatistas/yo/zona")
    def cambiar_zona(datos: ZonaEntrada, rescatista: Usuario = rescatista_actual):
        """#46: comunas de Cúcuta que cubre; lista vacía = toda la ciudad."""
        comunas = frozenset(datos.comunas)
        rescates.cambiar_zona(rescatista, comunas)
        return {"comunas": sorted(comunas)}

    @app.get("/rescatistas/yo")
    def mi_estado_de_rescatista(rescatista: Usuario = rescatista_actual):
        return {"disponible": rescates.esta_disponible(rescatista),
                "comunas": sorted(rescates.zona(rescatista))}

    @app.get("/rescates/ofertas")
    def ofertas_de_rescate(rescatista: Usuario = rescatista_actual):
        """Solo la comuna (ubicación aproximada); la dirección exacta se muestra al aceptar.
        «escalado»: nadie lo aceptó a tiempo y se ofrece en toda la ciudad (RF-23)."""
        escalados = rescates.escalados()
        return [{"codigo": r.codigo, "prioridad": r.prioridad.value,
                 "descripcion": r.descripcion, "comuna": r.ubicacion.comuna,
                 "escalado": r.codigo in escalados,
                 "esperando_desde": fecha_utc(r.creado_en)}
                for r in rescates.ofertas(rescatista)]

    @app.get("/rescates/mio")
    def mi_rescate(rescatista: Usuario = rescatista_actual):
        actual = rescates.mio(rescatista)
        return None if actual is None else _rescate(*actual)

    @app.get("/rescates/historial")
    def historial_de_rescates(rescatista: Usuario = rescatista_actual):
        """Mis rescates: los que aceptó, del más reciente al más viejo. Solo fechas y estados:
        la dirección exacta se muestra únicamente en el rescate en curso."""
        return [{"codigo": r.codigo, "aceptado_en": fecha_utc(r.aceptado_en),
                 "llego": r.estado in (EstadoRescate.EN_SITIO, EstadoRescate.ATENDIDO),
                 "llegada_en": fecha_utc(r.llegada_en) if r.llegada_en else None,
                 "resultado": r.resultado.value if r.resultado else None,
                 "estado": r.estado.value, "actualizado_en": fecha_utc(r.actualizado_en)}
                for r in repositorio_rescates.historial_de(rescatista.correo)]

    def _paso(accion, *args):
        try:
            return accion(*args)
        except RescateNoOfrecido as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PasoInvalido as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/rescates/{codigo}/aceptar")
    def aceptar_rescate(codigo: str, rescatista: Usuario = rescatista_actual):
        return _rescate(*_paso(rescates.aceptar, rescatista, codigo.upper()))

    @app.post("/rescates/{codigo}/llegue")
    def llegue_al_sitio(codigo: str, rescatista: Usuario = rescatista_actual):
        _paso(rescates.llegue, rescatista, codigo.upper())
        return {"codigo": codigo.upper(), "estado": "en_sitio"}

    @app.post("/rescates/{codigo}/liberar")
    def liberar_rescate(codigo: str, rescatista: Usuario = rescatista_actual):
        _paso(rescates.liberar, rescatista, codigo.upper())
        return {"codigo": codigo.upper(), "estado": "liberado"}

    @app.post("/rescates/{codigo}/resultado")
    def resultado_del_rescate(codigo: str, datos: ResultadoEntrada,
                              rescatista: Usuario = rescatista_actual):
        _paso(rescates.registrar_resultado, rescatista, codigo.upper(), datos.resultado)
        if datos.resultado in (ResultadoRescate.TRASLADADO, ResultadoRescate.ATENDIDO_EN_SITIO):
            avisar_al_ciudadano(codigo.upper(), (
                f"un rescatista ya atendió a tu animal del reporte {codigo.upper()}. "
                "Consulta cómo sigue con tu código en la página de seguimiento."))
        return {"codigo": codigo.upper(), "estado": "atendido",
                "resultado": datos.resultado.value}

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

    repositorio_piloto = repositorio_piloto or (
        RepositorioPilotoPostgres(motor) if motor is not None else RepositorioPilotoEnMemoria())
    app.include_router(crear_rutas_piloto(ServicioPiloto(repositorio_piloto), administracion,
                                          ReporteEntrada))  # RNF-06 (#258)
    app.include_router(crear_rutas_video(videos, almacen_videos, token_video, personal,
                                          almacen_vistas))
    app.mount("/app", StaticFiles(directory=CARPETA_PWA, html=True), name="pwa")
    app.mount("/inicio", StaticFiles(directory=CARPETA_INICIO), name="inicio")
    app.mount("/diseno", StaticFiles(directory=CARPETA_DISENO), name="diseno")
    if (CARPETA_PANEL / "index.html").exists():  # sin compilar, /panel no existe
        app.mount("/panel", StaticFiles(directory=CARPETA_PANEL, html=True), name="panel")

    @app.post("/refugio/ingresos", status_code=201)
    def registrar_ingreso(datos: IngresoEntrada, peticion: Request,
                          coordinador: Usuario = coordinacion):
        cupos = cupos_de(coordinador)
        antes = cupos.texto_ocupacion()
        codigo = normalizar_codigo(datos.reporte) if datos.reporte else None
        if codigo and repositorio.buscar(codigo) is None:
            raise HTTPException(status_code=422, detail="No existe un reporte con ese código.")
        try:
            cupos.registrar_ingreso(Animal(**datos.model_dump(exclude={"reporte"})))
        except CupoAgotado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if codigo:
            avisar_al_ciudadano(codigo, (
                f"el animal de tu reporte {codigo} ya ingresó al refugio. "
                "Consulta cómo sigue con tu código en la página de seguimiento."))
        _cambio(peticion, {"ocupacion": antes}, {"ocupacion": cupos.texto_ocupacion()})
        return {"ocupacion": cupos.texto_ocupacion()}

    # --- Fase 2 (#75): ficha clínica e historial (RF-06, RF-24) -----------------------

    @app.get("/refugio/animales")
    def animales_del_refugio(usuario: Usuario = personal):
        return [_ficha(a) for a in fichas_de(usuario).animales()]

    @app.get("/refugio/animales/{animal_id}")
    def ficha_clinica(animal_id: int, usuario: Usuario = personal):
        repo = fichas_de(usuario)
        animal = repo.animal(animal_id)
        if animal is None:
            raise HTTPException(status_code=404, detail="No hay ese animal en tu refugio.")
        return {**_ficha(animal), "historial": [
            {"tipo": n.tipo.value, "texto": n.texto, "autor": n.autor,
             "registrada_en": fecha_utc(n.registrada_en)} for n in repo.historial(animal_id)]}

    @app.post("/refugio/animales/{animal_id}/historial", status_code=201)
    def agregar_nota_clinica(animal_id: int, datos: NotaEntrada,
                             veterinario: Usuario = veterinaria):
        try:
            nota = ServicioFichas(fichas_de(veterinario)).agregar_nota(
                animal_id, veterinario, datos.tipo, datos.texto)
        except AnimalNoEncontrado as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except NotaInvalida as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"tipo": nota.tipo.value, "texto": nota.texto, "autor": nota.autor,
                "registrada_en": fecha_utc(nota.registrada_en)}

    @app.post("/refugio/animales/{animal_id}/egreso")
    def registrar_egreso(animal_id: int, datos: EgresoEntrada, peticion: Request,
                         coordinador: Usuario = coordinacion):
        """RF-26: como el ingreso, es del coordinador. 404 si no está en su refugio y 409 si
        ya egresó (el cupo no se libera dos veces)."""
        repo = fichas_de(coordinador)
        animal = repo.animal(animal_id)
        if animal is None:
            raise HTTPException(status_code=404, detail="No hay ese animal en tu refugio.")
        antes = cupos_de(coordinador).texto_ocupacion()
        refugio = repo.egresar(animal_id, datos.motivo)
        if refugio is None:
            raise HTTPException(status_code=409, detail=f"{animal.nombre} ya egresó.")
        _cambio(peticion, {"ocupacion": antes, "en_refugio": True},
                {"ocupacion": refugio.texto_ocupacion(), "en_refugio": False,
                 "motivo": datos.motivo.value})
        return {"ocupacion": refugio.texto_ocupacion()}

    @app.get("/refugio/ocupacion")
    def ocupacion(usuario: Usuario = personal):
        cupos = cupos_de(usuario)
        return {"ocupacion": cupos.texto_ocupacion(),
                "porcentaje": round(cupos.porcentaje_ocupacion() * 100, 1)}

    return app
