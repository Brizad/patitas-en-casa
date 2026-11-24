"""API REST del MVP de Patitas en Casa (FastAPI).

Se inicia con: uvicorn --factory app.api.main:crear_app
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    Request,
)
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine, create_engine

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
    cargar_ajustes_ip,
    cargar_ajustes_seguridad,
    cargar_ajustes_tareas,
)
from app.api.armado import (
    Repositorios,
    armar_repositorios,
    armar_video,
    cargar_demo_al_arrancar,
)
from app.api.comun import Contexto, ip_del_cliente
from app.api.middlewares import ciclo_de_vida, instalar_middlewares
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
from app.avisos.ciudadano import AvisosAlCiudadano
from app.avisos.procesador import ProcesadorAvisos
from app.avisos.repositorio import RepositorioAvisos
from app.bd.migraciones import verificar_migraciones
from app.bitacora.repositorio import RepositorioBitacora
from app.cupos.repositorio import RepositorioCupos
from app.cupos.servicio import Notificador, ServicioCupos
from app.demo import Dependencias
from app.dominio.modelos import (
    EstadoRescate,
    Prioridad,
    Reporte,
    Rol,
    Usuario,
)
from app.notificaciones.correo import crear_notificador
from app.observabilidad import instrumentar
from app.piloto.servicio import RepositorioPiloto, ServicioPiloto
from app.refugios.repositorio import RepositorioRefugios
from app.reportes.confirmacion import (
    ServicioConfirmacion,
)
from app.reportes.descarte import ServicioDescarte
from app.reportes.repositorio import RepositorioReportes
from app.reportes.servicio import ServicioReportes
from app.rescates.repositorio import RepositorioRescates
from app.rescates.servicio import (
    ServicioRescates,
)
from app.seguridad.cifrado import CanalConDescifrado, Cifrador
from app.seguridad.tokens import EmisorTokens
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
                          ("image/svg+xml", ".svg"), ("font/woff2", ".woff2")):
    mimetypes.add_type(_tipo, _extension)


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


# crear_app es la «raíz de composición»: arma los servicios y conecta las rutas
# (app/api/rutas_*.py, DT-13), los repositorios (armado.py) y los middlewares (#282).
def _tareas_activas(pedido: bool | None) -> bool:
    """#388: el parámetro de crear_app gana; si no hay, PATITAS_TAREAS_DE_FONDO (encendidas)."""
    activas = cargar_ajustes_tareas().tareas_de_fondo if pedido is None else pedido
    if not activas:
        logger.warning("Tareas de fondo APAGADAS (PATITAS_TAREAS_DE_FONDO=0): los avisos quedan "
                       "pendientes y no se revisan escalamientos ni videos.")
    return activas


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
              revisar_videos_cada_s: float | None = config.REVISION_VIDEOS_SEGUNDOS,
              tareas_de_fondo: bool | None = None) -> FastAPI:
    """Sin argumentos usa PostgreSQL, la clave JWT y el SMTP del .env; las pruebas inyectan
    dobles. Si se inyectan los tres repositorios y no el límite de intentos, los intentos
    fallidos se cuentan en memoria. Mientras la app corre se revisan los rescates sin aceptar
    cada «revisar_escalamientos_cada_s» segundos (None: no se revisan) y se envían los avisos
    pendientes cada «procesar_avisos_cada_s» (#63; None: solo a mano, como en las pruebas).
    Con «tareas_de_fondo» falso (o PATITAS_TAREAS_DE_FONDO=0 si no se pasa) no arranca ninguna
    (#388): los avisos quedan pendientes en la base y salen al encenderlas."""
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

    # #95: reglas + modelo entrenado (el modelo solo sube la prioridad); sin modelo, reglas.
    clasificador, version_triaje = triaje_por_defecto()
    reportes = ServicioReportes(repositorio, ServicioTriaje(clasificador, version=version_triaje))
    rescates = ServicioRescates(repositorio, repositorio_rescates, notificador=notificador,
                                avisos=repositorio_avisos)
    descartes = ServicioDescarte(repositorio)

    # RF-18: avisos al ciudadano que dejó un correo (app/avisos/ciudadano.py, #282).
    al_ciudadano = AvisosAlCiudadano(repositorio, repositorio_avisos, cifrador)
    avisar_al_ciudadano = al_ciudadano.avisar  # los routers del rescate y del refugio

    def avisos_al_confirmar(reporte: Reporte, prioridad: Prioridad):
        """Rescatistas de la zona (RF-05) y, si dejó un correo, el ciudadano (RF-18). El
        destinatario del ciudadano va cifrado también en la tabla de avisos."""
        return rescates.avisos_para(reporte, prioridad) + al_ciudadano.para(
            reporte, f"un veterinario revisó tu reporte {reporte.codigo}. "
            "Consulta cómo sigue con tu código en la página de seguimiento.")

    confirmaciones = ServicioConfirmacion(repositorio, planificar_avisos=avisos_al_confirmar)
    procesador = ProcesadorAvisos(repositorio_avisos, CanalConDescifrado(notificador, cifrador))
    # HU-06 (RF-23), #63 y #125: las tareas que se repiten mientras la app corre.
    periodicas = [(rescates.escalar_vencidos, revisar_escalamientos_cada_s,
                   "revisión de rescates sin aceptar"),
                  (procesador.procesar, procesar_avisos_cada_s, "envío de avisos pendientes"),
                  (videos.revisar, revisar_videos_cada_s if token_video else None,
                   "videos sin analizar a tiempo")]
    app = FastAPI(title="Patitas en Casa", version="1.3.0",
                  lifespan=ciclo_de_vida(periodicas if _tareas_activas(tareas_de_fondo) else [],
                                         motor))
    # Comprime con gzip lo que pase de 1 KB (el JS del panel baja de ~60 KB a ~20 KB): importa
    # en celulares con datos limitados (RNF-07).
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    instrumentar(app)  # FPI-29: no hace nada salvo con PATITAS_OBSERVABILIDAD=1
    app.state.procesador_avisos = procesador  # las pruebas lo ejecutan a mano
    app.state.bitacora = repositorio_bitacora
    app.state.usuarios = repositorio_usuarios  # las pruebas agregan cuentas
    servicios_demo = (reportes, confirmaciones, rescates, repositorio_cupos,
                      repositorio_adopciones)
    app.state.demo_servicios = servicios_demo
    cargar_demo_al_arrancar(motor, contrasena_demo,
                            Dependencias(repositorio_usuarios, *servicios_demo))

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
    ajustes_ip = ajustes_ip or (cargar_ajustes_ip() if motor is not None else AjustesIp())

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

    instalar_middlewares(app, repositorio_bitacora, emisor_tokens, token_video)

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
