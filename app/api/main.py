"""API REST del MVP de Patitas en Casa (FastAPI).

Se inicia con: uvicorn --factory app.api.main:crear_app
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import mimetypes
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

from app import config
from app.ajustes import (
    cargar_ajustes,
    cargar_ajustes_admin,
    cargar_ajustes_correo,
    cargar_ajustes_seguridad,
)
from app.api.seguridad import crear_dependencia_usuario, exigir_rol, no_autenticado
from app.avisos.procesador import ProcesadorAvisos
from app.avisos.repositorio import RepositorioAvisos, RepositorioAvisosEnMemoria, resumen
from app.avisos.repositorio_postgres import RepositorioAvisosPostgres
from app.bd.migraciones import verificar_migraciones
from app.cupos.repositorio import RepositorioCupos
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.cupos.servicio import CupoAgotado, Notificador, ServicioCupos
from app.dominio.modelos import (
    Animal,
    Especie,
    EstadoReporte,
    Prioridad,
    Refugio,
    Reporte,
    Rescate,
    ResultadoRescate,
    Rol,
    Ubicacion,
    Usuario,
)
from app.notificaciones.correo import crear_notificador
from app.refugios.repositorio import RepositorioRefugios, RepositorioRefugiosEnMemoria
from app.refugios.repositorio_postgres import RepositorioRefugiosPostgres
from app.reportes.confirmacion import (
    AjusteSinJustificacion,
    ReporteNoEncontrado,
    ReporteYaConfirmado,
    ServicioConfirmacion,
)
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
from app.seguridad.tokens import EmisorTokens
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


class VinculoEntrada(BaseModel):
    refugio_id: int | None  # None desvincula


def _refugio(refugio: Refugio) -> dict:
    return {"id": refugio.id, "nombre": refugio.nombre, "capacidad": refugio.capacidad,
            "ocupados": refugio.ocupados}


def _cuenta(usuario: Usuario) -> dict:
    return {"correo": usuario.correo, "nombre": usuario.nombre, "rol": usuario.rol.value,
            "activo": usuario.activo, "refugio_id": usuario.refugio_id}


class IngresoEntrada(BaseModel):
    nombre: str
    especie: Especie
    estado_salud: str
    vacunado: bool = False
    esterilizado: bool = False


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


def crear_app(repositorio: RepositorioReportes | None = None,
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
              repositorio_refugios: RepositorioRefugios | None = None) -> FastAPI:
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
    usuarios = ServicioUsuarios(repositorio_usuarios)
    dependencia_usuario = crear_dependencia_usuario(repositorio_usuarios, emisor_tokens)
    usuario_actual = Depends(dependencia_usuario)
    # DT-02: el personal se identifica con su token; X-Rol ya no existe.
    personal = exigir_rol(dependencia_usuario, *ROLES_PERSONAL)
    coordinacion = exigir_rol(dependencia_usuario, Rol.COORDINADOR)
    veterinaria = exigir_rol(dependencia_usuario, Rol.VETERINARIO)  # RN-06
    rescatista_actual = exigir_rol(dependencia_usuario, Rol.RESCATISTA)  # HU-06
    administracion = exigir_rol(dependencia_usuario, Rol.ADMINISTRADOR)  # #67

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

    app = FastAPI(title="Patitas en Casa", version="0.2.0", lifespan=ciclo_de_vida)
    reportes = ServicioReportes(repositorio, ServicioTriaje())
    rescates = ServicioRescates(repositorio, repositorio_rescates, notificador=notificador)
    confirmaciones = ServicioConfirmacion(repositorio, planificar_avisos=rescates.avisos_para)
    procesador = ProcesadorAvisos(repositorio_avisos, notificador)
    app.state.procesador_avisos = procesador  # las pruebas lo ejecutan a mano
    cupos = ServicioCupos(repositorio_cupos, notificador)

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

    @app.get("/admin/refugios")
    def listar_refugios(_admin: Usuario = administracion):
        return [_refugio(r) for r in repositorio_refugios.todos()]

    @app.post("/admin/refugios", status_code=201)
    def registrar_refugio(datos: RefugioEntrada, _admin: Usuario = administracion):
        """RF-14: el refugio nace sin animales; sus cupos los usa el coordinador."""
        if not datos.nombre.strip():
            raise HTTPException(status_code=422, detail="El nombre del refugio es obligatorio.")
        return _refugio(repositorio_refugios.crear(datos.nombre.strip(), datos.capacidad))

    @app.put("/admin/usuarios/{correo}/refugio")
    def vincular_a_refugio(correo: str, datos: VinculoEntrada,
                           _admin: Usuario = administracion):
        correo = normalizar_correo(correo)
        if datos.refugio_id is not None and not repositorio_refugios.existe(datos.refugio_id):
            raise HTTPException(status_code=404, detail="Ese refugio no existe.")
        if not repositorio_usuarios.vincular_refugio(correo, datos.refugio_id):
            raise HTTPException(status_code=404, detail="No existe una cuenta con ese correo.")
        return {"correo": correo, "refugio_id": datos.refugio_id}

    @app.post("/reportes", status_code=201)
    def crear_reporte(datos: ReporteEntrada, respuesta: Response,
                      clave: ClaveIdempotencia = None):
        """RF-01. RF-12 (#61): con Idempotency-Key, reenviar el mismo reporte devuelve el mismo
        código con 200 en vez de crear otro; sin el encabezado funciona como antes."""
        ubicacion = Ubicacion(datos.latitud, datos.longitud, datos.direccion, datos.comuna)
        video = (datos.video_segundos, datos.video_mb)
        try:
            if clave is None:
                r = reportes.registrar(datos.descripcion, ubicacion, *video)
            else:
                r, nuevo = reportes.registrar_una_vez(clave, datos.descripcion, ubicacion, *video)
                if not nuevo:
                    respuesta.status_code = status.HTTP_200_OK
        except ReporteInvalido as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
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
        pasos, ultimo_cambio = linea_de_tiempo(
            reporte, decisiones[-1] if decisiones else None, repositorio_rescates.vigente(codigo))
        return {"codigo": codigo, "ultimo_cambio": fecha_utc(ultimo_cambio),
                "pasos": [{"nombre": p.nombre, "estado": p.estado, "detalle": p.detalle,
                           "fecha": fecha_utc(p.fecha)} for p in pasos]}

    @app.get("/cola", dependencies=[personal])
    def cola():
        """Reportes pendientes de confirmar (HU-02); los confirmados salen de la cola."""
        pendientes = [r for r in repositorio.todos() if r.estado != EstadoReporte.CONFIRMADO]
        return [
            {"codigo": r.codigo, "prioridad": r.prioridad.value, "estado": r.estado.value,
             "confianza": r.confianza, "evidencias": r.evidencias}
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
                 "decidido_en": fecha_utc(d.decidido_en)}
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

    @app.get("/", include_in_schema=False)
    def inicio():
        return RedirectResponse("/app/")

    app.mount("/app", StaticFiles(directory=CARPETA_PWA, html=True), name="pwa")
    if (CARPETA_PANEL / "index.html").exists():  # sin compilar, /panel no existe
        app.mount("/panel", StaticFiles(directory=CARPETA_PANEL, html=True), name="panel")

    @app.post("/refugio/ingresos", status_code=201, dependencies=[coordinacion])
    def registrar_ingreso(datos: IngresoEntrada):
        try:
            cupos.registrar_ingreso(Animal(**datos.model_dump()))
        except CupoAgotado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"ocupacion": cupos.texto_ocupacion()}

    @app.get("/refugio/ocupacion", dependencies=[personal])
    def ocupacion():
        return {"ocupacion": cupos.texto_ocupacion(),
                "porcentaje": round(cupos.porcentaje_ocupacion() * 100, 1)}

    return app
