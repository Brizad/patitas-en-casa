"""API REST del MVP de Patitas en Casa (FastAPI).

Se inicia con: uvicorn --factory app.api.main:crear_app
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import mimetypes
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
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
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Engine, create_engine
from starlette.concurrency import run_in_threadpool

from app import config
from app.adopciones.asignacion import asignar
from app.adopciones.compatibilidad import Compatibilidad, calcular, recomendar
from app.adopciones.compromiso import lineas_compromiso
from app.adopciones.modelos import (
    Energia,
    EstadoSolicitud,
    PerfilAdoptante,
    Publicacion,
    Seguimiento,
    Tamano,
    Vivienda,
)
from app.adopciones.repositorio import RepositorioAdopciones, RepositorioAdopcionesEnMemoria
from app.adopciones.repositorio_postgres import RepositorioAdopcionesPostgres
from app.adopciones.servicio import (
    AnimalNoDisponible,
    PerfilIncompleto,
    RazonInvalida,
    RestriccionDura,
    SeguimientoNoValido,
    ServicioAdopciones,
    SolicitudNoEncontrada,
    SolicitudRepetida,
    SolicitudYaDecidida,
)
from app.ajustes import (
    cargar_ajustes,
    cargar_ajustes_admin,
    cargar_ajustes_correo,
    cargar_ajustes_datos,
    cargar_ajustes_demo,
    cargar_ajustes_seguridad,
)
from app.api.seguridad import crear_dependencia_usuario, exigir_rol, no_autenticado
from app.avisos.modelos import AvisoNuevo
from app.avisos.procesador import ProcesadorAvisos
from app.avisos.repositorio import RepositorioAvisos, RepositorioAvisosEnMemoria, resumen
from app.avisos.repositorio_postgres import RepositorioAvisosPostgres
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
    DECIDIDOS,
    Animal,
    Especie,
    EstadoReporte,
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
from app.indicadores.calculo import Datos
from app.indicadores.calculo import calcular as calcular_indicadores
from app.indicadores.exportar import a_csv, filas_anonimizadas, resumen_pdf
from app.notificaciones.correo import crear_notificador
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
from app.usuarios.contrasenas import ContrasenaInvalida
from app.usuarios.intentos import (
    LimiteIntentos,
    RepositorioIntentosEnMemoria,
    clave_correo,
    clave_ip,
)
from app.usuarios.intentos_postgres import RepositorioIntentosPostgres
from app.usuarios.repositorio import CorreoDuplicado, RepositorioUsuarios
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import (
    PATRON_CORREO,
    AutoSuspension,
    CuentaNoEncontrada,
    ServicioUsuarios,
    normalizar_correo,
)

logger = logging.getLogger(__name__)

# HU-08 (#47): la PWA ciudadana (HTML + JS sencillos) la sirve la misma API en /app/.
CARPETA_PWA = Path(__file__).resolve().parents[1] / "pwa"
# II-03 (#64): panel del personal en React; se compila con «npm run build» en panel/.
CARPETA_PANEL = Path(__file__).resolve().parents[1] / "panel_web"
# Windows puede asociar .js a text/plain en el registro; el navegador exige estos tipos.
for _tipo, _extension in (("text/javascript", ".js"), ("text/css", ".css"),
                          ("application/manifest+json", ".webmanifest"),
                          ("image/svg+xml", ".svg")):
    mimetypes.add_type(_tipo, _extension)
# Solo recursos del propio servidor: sin scripts en línea ni de terceros (XSS).
POLITICA_PWA = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
                "connect-src 'self'; manifest-src 'self'; worker-src 'self'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")

# Pueden usar /cola y /refugio/ocupacion. Públicos (RF-01): POST /reportes y
# GET /reportes/{codigo}. POST /refugio/ingresos es solo del coordinador (P-06 del prototipo).
ROLES_PERSONAL = (Rol.VETERINARIO, Rol.COORDINADOR)


class ReporteEntrada(BaseModel):
    descripcion: str
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = None
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


def fecha_utc(fecha: datetime | None) -> str | None:
    """D-06: toda fecha de la API sale en UTC («+00:00»). PostgreSQL devuelve la hora en la
    zona de la sesión (en Cúcuta, -05:00): es el mismo instante, pero dos formatos confunden."""
    return None if fecha is None else fecha.astimezone(UTC).isoformat()


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


class CuentaEntrada(BaseModel):
    """#67: el administrador crea cuentas del personal (la contraseña nunca se devuelve)."""

    correo: str = Field(max_length=254)
    nombre: str = Field(max_length=120)
    rol: Rol
    contrasena: str = Field(max_length=128)


class ActivoEntrada(BaseModel):
    activo: bool


class RefugioEntrada(BaseModel):
    nombre: str = Field(max_length=120)
    capacidad: int = Field(gt=0, le=10_000)
    direccion: str = Field(default="", max_length=200)  # #108 (RF-14)


class VinculoEntrada(BaseModel):
    refugio_id: int | None  # None desvincula


def _refugio(refugio: Refugio) -> dict:
    return {"id": refugio.id, "nombre": refugio.nombre, "capacidad": refugio.capacidad,
            "ocupados": refugio.ocupados, "direccion": refugio.direccion}


def _cuenta(usuario: Usuario) -> dict:
    return {"correo": usuario.correo, "nombre": usuario.nombre, "rol": usuario.rol.value,
            "activo": usuario.activo, "refugio_id": usuario.refugio_id}


class IngresoEntrada(BaseModel):
    nombre: str
    especie: Especie
    estado_salud: str
    vacunado: bool = False
    esterilizado: bool = False


class EgresoEntrada(BaseModel):
    motivo: MotivoEgreso


class RegistroAdoptante(BaseModel):
    """RF-08: registro público. Sin autorizar el tratamiento de datos no hay cuenta."""

    correo: str = Field(max_length=254)
    nombre: str = Field(max_length=120)
    contrasena: str = Field(max_length=128)
    autoriza_datos: bool  # Ley 1581 de 2012


class PerfilEntrada(BaseModel):
    vivienda: Vivienda
    tiene_patio: bool
    hay_ninos: bool
    otros_animales: bool
    horas_solo_al_dia: int = Field(ge=0, le=24)
    experiencia: bool
    acepta_seguimiento: bool


class PublicacionEntrada(BaseModel):
    descripcion: str = Field(min_length=20, max_length=1000)
    tamano: Tamano
    energia: Energia
    edad_meses: int = Field(ge=0, le=360)
    apto_ninos: bool
    apto_otros_animales: bool
    necesita_patio: bool


def _publicacion(p: Publicacion) -> dict:
    return {"animal_id": p.animal_id, "nombre": p.nombre, "especie": p.especie,
            "descripcion": p.descripcion, "tamano": p.tamano.value, "energia": p.energia.value,
            "edad_meses": p.edad_meses, "apto_ninos": p.apto_ninos,
            "apto_otros_animales": p.apto_otros_animales, "necesita_patio": p.necesita_patio,
            "estado": p.estado.value, "publicado_en": fecha_utc(p.publicado_en)}


class SolicitudEntrada(BaseModel):
    animal_id: int
    mensaje: str = Field(default="", max_length=1000)


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


def _compatibilidad(c: Compatibilidad) -> dict:
    return {"puntaje": c.puntaje, "razones": c.razones, "alertas": c.alertas,
            "restricciones": c.restricciones}


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
              cifrador: Cifrador | None = None) -> FastAPI:
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
    repositorio_adopciones = repositorio_adopciones or (
        RepositorioAdopcionesPostgres(motor) if motor is not None
        else RepositorioAdopcionesEnMemoria(repositorio_cupos))
    repositorio_bitacora = repositorio_bitacora or (
        RepositorioBitacoraPostgres(motor) if motor is not None
        else RepositorioBitacoraEnMemoria())
    if cifrador is None and motor is not None:
        clave_datos = cargar_ajustes_datos().clave_datos
        cifrador = Cifrador(clave_datos.get_secret_value()) if clave_datos else None
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
        yield
        for tarea in tareas:
            tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarea
        if motor is not None:
            motor.dispose()

    app = FastAPI(title="Patitas en Casa", version="1.0.0", lifespan=ciclo_de_vida)
    # #95: reglas + modelo entrenado (el modelo solo sube la prioridad); sin modelo, reglas.
    clasificador, version_triaje = triaje_por_defecto()
    reportes = ServicioReportes(repositorio, ServicioTriaje(clasificador, version=version_triaje))
    rescates = ServicioRescates(repositorio, repositorio_rescates, notificador=notificador)
    descartes = ServicioDescarte(repositorio)

    def avisos_al_confirmar(reporte: Reporte, prioridad: Prioridad):
        """Rescatistas de la zona (RF-05) y, si dejó un correo, el ciudadano (RF-18). El
        destinatario del ciudadano va cifrado también en la tabla de avisos."""
        avisos = rescates.avisos_para(reporte, prioridad)
        if reporte.contacto_cifrado and cifrador is not None:
            if "@" in cifrador.descifrar(reporte.contacto_cifrado):
                avisos.append(AvisoNuevo(
                    PREFIJO_AVISO + reporte.contacto_cifrado,
                    f"Patitas en Casa: un veterinario revisó tu reporte {reporte.codigo}. "
                    "Consulta cómo sigue con tu código en la página de seguimiento."))
        return avisos

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

    @app.post("/auth/token")
    def iniciar_sesion(formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
                       peticion: Request):
        """Inicio de sesión del personal: username = correo (DT-02).

        DT-06: con demasiados fallos recientes del correo o de la IP responde 429 sin mirar
        la contraseña, ni siquiera la correcta: así el atacante no sabe si acertó.
        """
        # La IP es la de la conexión; X-Forwarded-For no se usa porque el cliente la inventa.
        ip = peticion.client.host if peticion.client else "desconocida"
        claves = [clave_correo(normalizar_correo(formulario.username)), clave_ip(ip)]
        espera = limite_intentos.segundos_de_bloqueo(claves)
        if espera:
            # Sin correo ni contraseña en el log: solo la IP y la espera.
            logger.warning("Inicio de sesión bloqueado por intentos fallidos (IP %s, %d s).",
                           ip, espera)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos fallidos. Intenta de nuevo en {espera} segundos.",
                headers={"Retry-After": str(espera)})
        usuario = usuarios.autenticar(formulario.username, formulario.password)
        if usuario is None:
            limite_intentos.registrar_fallo(claves)
            # Mismo mensaje exista o no el correo: no se revela qué cuentas existen.
            raise no_autenticado("Correo o contraseña incorrectos.")
        limite_intentos.registrar_exito(claves[0])
        # RF-16: historial de acceso de la cuenta (en la bitácora, también inmutable).
        repositorio_bitacora.registrar(Evento(usuario.correo, "inicio de sesión", {}, 200))
        return {"access_token": emisor_tokens.emitir(usuario), "token_type": "bearer",
                "expira_en": emisor_tokens.minutos * 60}

    @app.get("/auth/yo")
    def mi_cuenta(usuario: Usuario = usuario_actual):
        return {"correo": usuario.correo, "nombre": usuario.nombre, "rol": usuario.rol.value}

    # --- Fase 1 (#67): administración de cuentas (RF-13, RF-16) -------------------------

    @app.get("/admin/usuarios")
    def listar_cuentas(_admin: Usuario = administracion):
        return [_cuenta(u) for u in usuarios.listar()]

    @app.post("/admin/usuarios", status_code=201)
    def crear_cuenta(datos: CuentaEntrada, _admin: Usuario = administracion):
        try:
            nueva = usuarios.registrar(datos.correo, datos.nombre, datos.rol, datos.contrasena)
        except CorreoDuplicado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (ContrasenaInvalida, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _cuenta(nueva)

    @app.put("/admin/usuarios/{correo}/activo")
    def suspender_o_reactivar(correo: str, datos: ActivoEntrada,
                              admin: Usuario = administracion):
        """RF-16: una cuenta suspendida pierde el acceso en la siguiente petición, porque
        la dependencia de sesión relee la cuenta (no basta con tener un token vigente)."""
        try:
            usuarios.cambiar_activo(admin, correo, datos.activo)
        except AutoSuspension as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except CuentaNoEncontrada as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return {"correo": normalizar_correo(correo), "activo": datos.activo}

    @app.get("/admin/usuarios/{correo}/accesos")
    def historial_de_acceso(correo: str, _admin: Usuario = administracion):
        """RF-16: inicios de sesión de la cuenta, el más reciente primero."""
        return [{"momento": fecha_utc(e.momento)} for e in repositorio_bitacora.de_actor(
            normalizar_correo(correo), "inicio de sesión")]

    @app.get("/admin/refugios")
    def listar_refugios(_admin: Usuario = administracion):
        return [_refugio(r) for r in repositorio_refugios.todos()]

    @app.post("/admin/refugios", status_code=201)
    def registrar_refugio(datos: RefugioEntrada, _admin: Usuario = administracion):
        """RF-14: el refugio nace sin animales; sus cupos los usa el coordinador."""
        if not datos.nombre.strip():
            raise HTTPException(status_code=422, detail="El nombre del refugio es obligatorio.")
        return _refugio(repositorio_refugios.crear(datos.nombre.strip(), datos.capacidad,
                                                   datos.direccion.strip()))

    @app.put("/admin/usuarios/{correo}/refugio")
    def vincular_a_refugio(correo: str, datos: VinculoEntrada,
                           _admin: Usuario = administracion):
        correo = normalizar_correo(correo)
        if datos.refugio_id is not None and not repositorio_refugios.existe(datos.refugio_id):
            raise HTTPException(status_code=404, detail="Ese refugio no existe.")
        if not repositorio_usuarios.vincular_refugio(correo, datos.refugio_id):
            raise HTTPException(status_code=404, detail="No existe una cuenta con ese correo.")
        return {"correo": correo, "refugio_id": datos.refugio_id}

    # --- Fase 3 (#85): adoptante (RF-08) ---------------------------------------------

    @app.post("/adoptantes", status_code=201)
    def registrar_adoptante(datos: RegistroAdoptante):
        """Público, como el reporte: el adoptante no es personal y crea su propia cuenta.
        El rol siempre es adoptante; nadie puede registrarse como personal por aquí."""
        if not datos.autoriza_datos:
            raise HTTPException(status_code=422, detail=(
                "Para crear la cuenta debes autorizar el tratamiento de tus datos "
                "(Ley 1581 de 2012)."))
        try:
            nueva = usuarios.registrar(datos.correo, datos.nombre, Rol.ADOPTANTE,
                                       datos.contrasena)
        except CorreoDuplicado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (ContrasenaInvalida, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"correo": nueva.correo, "rol": nueva.rol.value}

    @app.get("/adoptantes/yo/perfil")
    def mi_perfil(adoptante: Usuario = adoptante_actual):
        perfil = repositorio_adopciones.perfil(adoptante.correo)
        if perfil is None:
            raise HTTPException(status_code=404, detail="Aún no has llenado tu perfil.")
        return {**{k: v for k, v in vars(perfil).items() if k != "actualizado_en"},
                "actualizado_en": fecha_utc(perfil.actualizado_en)}

    @app.put("/adoptantes/yo/perfil")
    def guardar_mi_perfil(datos: PerfilEntrada, adoptante: Usuario = adoptante_actual):
        repositorio_adopciones.guardar_perfil(
            PerfilAdoptante(correo=adoptante.correo, **datos.model_dump()))
        return {"correo": adoptante.correo, "guardado": True}

    @app.post("/refugio/animales/{animal_id}/publicacion", status_code=201)
    def publicar_animal(animal_id: int, datos: PublicacionEntrada,
                        coordinador: Usuario = coordinacion):
        """RF-25: el coordinador publica un animal de su refugio que sigue allí."""
        animal = fichas_de(coordinador).animal(animal_id)
        if animal is None:
            raise HTTPException(status_code=404, detail="No hay ese animal en tu refugio.")
        if animal.egresado_en is not None:
            raise HTTPException(status_code=409, detail=f"{animal.nombre} ya egresó.")
        publicacion = Publicacion(animal_id=animal_id, nombre=animal.nombre,
                                  especie=animal.especie.value, **datos.model_dump())
        if not repositorio_adopciones.publicar(publicacion):
            raise HTTPException(status_code=409, detail=f"{animal.nombre} ya está publicado.")
        return _publicacion(publicacion)

    @app.get("/adopciones/animales")
    def catalogo_de_adopcion():
        """Público: animales disponibles. Sin datos del refugio ni de personas (RN-14)."""
        return [_publicacion(p) for p in repositorio_adopciones.disponibles()]

    @app.get("/adopciones/recomendaciones")
    def recomendaciones(adoptante: Usuario = adoptante_actual):
        """RF-09: animales disponibles ordenados por compatibilidad con SU hogar, con puntaje
        y 3 razones. Los que tienen una restricción dura (RN-05) no aparecen."""
        perfil = repositorio_adopciones.perfil(adoptante.correo)
        if perfil is None:
            raise HTTPException(status_code=422, detail="Llena tu perfil para ver "
                                "recomendaciones.")
        return [{**_publicacion(a), **_compatibilidad(c)}
                for a, c in recomendar(perfil, repositorio_adopciones.disponibles())]

    @app.post("/adopciones/solicitudes", status_code=201)
    def solicitar_adopcion(datos: SolicitudEntrada, adoptante: Usuario = adoptante_actual):
        """RF-27, RN-10: perfil lleno y seguimiento aceptado; una pendiente por animal."""
        try:
            s = adopciones.solicitar(adoptante, datos.animal_id, datos.mensaje)
        except PerfilIncompleto as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except AnimalNoDisponible as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SolicitudRepetida as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"id": s.id, "animal_id": s.animal_id, "estado": s.estado.value}

    @app.get("/adopciones/solicitudes/mias")
    def mis_solicitudes(adoptante: Usuario = adoptante_actual):
        return [{"id": s.id, "animal_id": s.animal_id, "estado": s.estado.value,
                 "creada_en": fecha_utc(s.creada_en)}
                for s in repositorio_adopciones.solicitudes() if s.adoptante == adoptante.correo]

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
    def decidir_solicitud(solicitud_id: int, datos: DecisionEntrada,
                          coordinador: Usuario = coordinacion):
        """RF-27: aprobar (RN-05, RN-11; egreso por adopción y seguimientos RF-10) o
        rechazar con razón. Solo solicitudes de animales de su refugio."""
        solicitud = repositorio_adopciones.solicitud(solicitud_id)
        if solicitud is None or fichas_de(coordinador).animal(solicitud.animal_id) is None:
            raise HTTPException(status_code=404, detail="No hay esa solicitud en tu refugio.")
        try:
            s = adopciones.decidir(coordinador, solicitud_id, datos.aprobar, datos.razon)
        except SolicitudNoEncontrada as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (SolicitudYaDecidida, RestriccionDura) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RazonInvalida as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": s.id, "estado": s.estado.value, "razon": s.razon,
                "seguimientos": [{"dia": x.dia, "programado_para": fecha_utc(x.programado_para)}
                                 for x in repositorio_adopciones.seguimientos(solicitud_id)]}

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

    @app.post("/reportes", status_code=201)
    def crear_reporte(datos: ReporteEntrada, respuesta: Response,
                      clave: ClaveIdempotencia = None):
        """RF-01. RF-12 (#61): con Idempotency-Key, reenviar el mismo reporte devuelve el mismo
        código con 200 en vez de crear otro; sin el encabezado funciona como antes."""
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
        r = repositorio.buscar(codigo.upper())
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
        todos = repositorio.todos()
        pendientes = [r for r in todos if r.estado not in DECIDIDOS]
        return [
            {"codigo": r.codigo, "prioridad": r.prioridad.value, "estado": r.estado.value,
             "confianza": r.confianza, "evidencias": r.evidencias,
             "version_modelo": r.version_modelo,
             # RF-17: se compara también con los ya confirmados (el original suele estarlo).
             "posibles_duplicados": posibles_duplicados(r, todos)}
            for r in ordenar_cola(pendientes)
        ]

    @app.post("/reportes/{codigo}/confirmacion")
    def confirmar_prioridad(codigo: str, datos: ConfirmacionEntrada,
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
        if decision.prioridad_final not in PRIORIDADES_DE_RESCATE:
            estado_aviso = "no_aplica"  # media y baja las programa el refugio
        else:
            estado_aviso = "pendiente" if resultado.avisos else "sin_destinatarios"
        return {"codigo": decision.codigo, "estado": EstadoReporte.CONFIRMADO.value,
                "prioridad": decision.prioridad_final.value, "ajustada": decision.ajustada,
                "avisos": {"programados": resultado.avisos, "estado": estado_aviso}}

    @app.post("/reportes/{codigo}/descarte")
    def descartar_reporte(codigo: str, datos: DescarteEntrada,
                          veterinario: Usuario = veterinaria):
        """D-02: falso o duplicado. Como confirmar, sale de la cola y es una sola vez (409)."""
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
        return {"codigo": codigo.upper(), "estado": "atendido",
                "resultado": datos.resultado.value}

    # --- HU-08: PWA ciudadana (#59) --------------------------------------------------

    @app.middleware("http")
    async def cabeceras_de_la_pwa(peticion: Request, siguiente):
        respuesta = await siguiente(peticion)
        if peticion.url.path.startswith(("/app", "/panel")):
            respuesta.headers["Content-Security-Policy"] = POLITICA_PWA
            respuesta.headers["X-Content-Type-Options"] = "nosniff"
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
            actor = "anónimo"
            token = peticion.headers.get("authorization", "").removeprefix("Bearer ")
            if token:
                with contextlib.suppress(TokenInvalido):
                    actor = emisor_tokens.validar(token).correo
            try:
                # En un hilo: el INSERT no debe frenar las demás peticiones (async).
                await run_in_threadpool(repositorio_bitacora.registrar, Evento(
                    actor, f"{peticion.method} {ruta.path}",
                    {k: str(v) for k, v in peticion.path_params.items()},
                    respuesta.status_code))
            except Exception:
                # La acción ya ocurrió; no se le dice al usuario que falló. Queda en el log.
                logger.exception("No se pudo registrar en la bitácora: %s", ruta.path)
        return respuesta

    def datos_para_indicadores() -> Datos:
        reportes_ = repositorio.todos()
        decisiones = {}
        for r in reportes_:
            lista = repositorio.decisiones(r.codigo)
            if lista:
                decisiones[r.codigo] = lista[-1]
        rescates_ = [x for x in (repositorio_rescates.vigente(c) for c in decisiones) if x]
        solicitudes_ = repositorio_adopciones.solicitudes()
        seguimientos_ = [x for s in solicitudes_ for x in repositorio_adopciones.seguimientos(s.id)]
        return Datos(reportes_, decisiones, rescates_, repositorio_refugios.todos(),
                     solicitudes_, seguimientos_)

    @app.get("/indicadores", dependencies=[gestion])
    def indicadores():
        """RF-30: conteos, porcentajes y tiempos; ningún dato personal. Se calculan al pedirlos
        (pocos datos: no hace falta un almacén aparte)."""
        return calcular_indicadores(datos_para_indicadores(), datetime.now(UTC))

    @app.get("/indicadores/reportes.csv", dependencies=[gestion])
    def exportar_reportes_csv():
        """RF-31: una fila por reporte, sin descripción, dirección, GPS, hora ni código."""
        d = datos_para_indicadores()
        return Response(a_csv(filas_anonimizadas(d.reportes, d.decisiones)),
                        media_type="text/csv; charset=utf-8", headers={
                            "Content-Disposition": 'attachment; filename="reportes.csv"'})

    @app.get("/indicadores/resumen.pdf", dependencies=[gestion])
    def exportar_resumen_pdf():
        ahora = datetime.now(UTC)
        pdf = resumen_pdf(calcular_indicadores(datos_para_indicadores(), ahora),
                          ahora.strftime("%Y-%m-%d %H:%M"))
        return Response(pdf, media_type="application/pdf", headers={
            "Content-Disposition": 'attachment; filename="indicadores.pdf"'})

    @app.get("/bitacora")
    def ver_bitacora(limite: int = 100, _admin: Usuario = administracion):
        return [{"momento": fecha_utc(e.momento), "actor": e.actor, "accion": e.accion,
                 "objeto": e.objeto, "estado_http": e.estado_http}
                for e in repositorio_bitacora.recientes(min(max(limite, 1), 500))]

    @app.get("/", include_in_schema=False)
    def inicio():
        return RedirectResponse("/app/")

    app.mount("/app", StaticFiles(directory=CARPETA_PWA, html=True), name="pwa")
    if (CARPETA_PANEL / "index.html").exists():  # sin compilar, /panel no existe
        app.mount("/panel", StaticFiles(directory=CARPETA_PANEL, html=True), name="panel")

    @app.post("/refugio/ingresos", status_code=201)
    def registrar_ingreso(datos: IngresoEntrada, coordinador: Usuario = coordinacion):
        cupos = cupos_de(coordinador)
        try:
            cupos.registrar_ingreso(Animal(**datos.model_dump()))
        except CupoAgotado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
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
    def registrar_egreso(animal_id: int, datos: EgresoEntrada,
                         coordinador: Usuario = coordinacion):
        """RF-26: como el ingreso, es del coordinador. 404 si no está en su refugio y 409 si
        ya egresó (el cupo no se libera dos veces)."""
        repo = fichas_de(coordinador)
        animal = repo.animal(animal_id)
        if animal is None:
            raise HTTPException(status_code=404, detail="No hay ese animal en tu refugio.")
        refugio = repo.egresar(animal_id, datos.motivo)
        if refugio is None:
            raise HTTPException(status_code=409, detail=f"{animal.nombre} ya egresó.")
        return {"ocupacion": refugio.texto_ocupacion()}

    @app.get("/refugio/ocupacion")
    def ocupacion(usuario: Usuario = personal):
        cupos = cupos_de(usuario)
        return {"ocupacion": cupos.texto_ocupacion(),
                "porcentaje": round(cupos.porcentaje_ocupacion() * 100, 1)}

    return app
