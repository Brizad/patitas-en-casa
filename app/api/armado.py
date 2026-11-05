"""Armado de los repositorios de la API (#282): memoria (pruebas) o PostgreSQL (producción).

Antes vivía dentro de crear_app; aquí la regla es una sola: lo que la prueba inyecta se usa
tal cual y lo que falta sale de la base del .env (o, sin base, de memoria).
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import NamedTuple

from sqlalchemy import Engine

from app import config
from app.adopciones.fotos import RepositorioFotos, RepositorioFotosEnMemoria
from app.adopciones.fotos_postgres import RepositorioFotosPostgres
from app.adopciones.repositorio import RepositorioAdopciones, RepositorioAdopcionesEnMemoria
from app.adopciones.repositorio_postgres import RepositorioAdopcionesPostgres
from app.ajustes import (
    cargar_ajustes_admin,
    cargar_ajustes_datos,
    cargar_ajustes_demo,
    cargar_ajustes_video,
)
from app.avisos.repositorio import RepositorioAvisos, RepositorioAvisosEnMemoria
from app.avisos.repositorio_postgres import RepositorioAvisosPostgres
from app.bd.esquema import vistas_trozos
from app.bitacora.repositorio import RepositorioBitacora, RepositorioBitacoraEnMemoria
from app.bitacora.repositorio_postgres import RepositorioBitacoraPostgres
from app.cupos.repositorio import RepositorioCupos
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.demo import Dependencias, cargar_demo
from app.dominio.modelos import Refugio
from app.piloto.repositorio_postgres import RepositorioPilotoPostgres
from app.piloto.servicio import RepositorioPiloto, RepositorioPilotoEnMemoria
from app.refugios.repositorio import RepositorioRefugios, RepositorioRefugiosEnMemoria
from app.refugios.repositorio_postgres import RepositorioRefugiosPostgres
from app.reportes.repositorio import RepositorioReportes
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.rescates.repositorio import RepositorioRescates, RepositorioRescatesEnMemoria
from app.rescates.repositorio_postgres import RepositorioRescatesPostgres
from app.seguridad.cifrado import Cifrador
from app.usuarios.admin_inicial import crear_admin_inicial
from app.usuarios.intentos import LimiteIntentos, RepositorioIntentosEnMemoria
from app.usuarios.intentos_postgres import RepositorioIntentosPostgres
from app.usuarios.repositorio import RepositorioUsuarios
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.video.almacen import AlmacenEnDisco, AlmacenEnPostgres
from app.video.repositorio import RepositorioVideos, RepositorioVideosEnMemoria
from app.video.repositorio_postgres import RepositorioVideosPostgres

logger = logging.getLogger("app.api.main")  # el mismo de antes: los logs no cambian


class Repositorios(NamedTuple):
    """Los mismos nombres que los parámetros de crear_app: se desempaca en sus variables."""
    repositorio: RepositorioReportes | None = None
    repositorio_cupos: RepositorioCupos | None = None
    repositorio_usuarios: RepositorioUsuarios | None = None
    limite_intentos: LimiteIntentos | None = None
    repositorio_rescates: RepositorioRescates | None = None
    repositorio_avisos: RepositorioAvisos | None = None
    repositorio_refugios: RepositorioRefugios | None = None
    cifrador: Cifrador | None = None
    repositorio_adopciones: RepositorioAdopciones | None = None
    repositorio_bitacora: RepositorioBitacora | None = None
    repositorio_fotos: RepositorioFotos | None = None
    repositorio_videos: RepositorioVideos | None = None
    repositorio_piloto: RepositorioPiloto | None = None


def armar_repositorios(dados: Repositorios,
                       motor_desde_entorno) -> tuple[Repositorios, Engine | None]:
    """Si falta alguno de los tres repositorios principales, se abre la base del .env (y se
    crea la primera cuenta de administración, #67). Devuelve todos los repositorios y el motor
    (None sin base)."""
    motor = None
    if None in (dados.repositorio, dados.repositorio_cupos, dados.repositorio_usuarios):
        motor = motor_desde_entorno()
        dados = dados._replace(
            repositorio=dados.repositorio or RepositorioPostgres(motor),
            repositorio_cupos=(dados.repositorio_cupos
                               or RepositorioCuposPostgres.primer_refugio(motor)),
            repositorio_usuarios=(dados.repositorio_usuarios
                                  or RepositorioUsuariosPostgres(motor)))
        # #67: en Render no hay consola; la primera cuenta de administración sale del entorno.
        crear_admin_inicial(dados.repositorio_usuarios, cargar_ajustes_admin())
    armar = _con_base if motor is not None else _en_memoria
    return armar(dados, motor), motor


def _con_base(dados: Repositorios, motor: Engine) -> Repositorios:
    cifrador = dados.cifrador
    if cifrador is None:
        ajustes = cargar_ajustes_datos()
        cifrador = (Cifrador(ajustes.clave_datos.get_secret_value(), ajustes.clave_kdf)
                    if ajustes.clave_datos else None)
    adopciones = dados.repositorio_adopciones
    if adopciones is None:
        # RNF-08 (#149): perfiles cifrados; los que estaban en claro se cifran al arrancar.
        adopciones = RepositorioAdopcionesPostgres(motor, cifrador)
        cifrados = adopciones.cifrar_perfiles_en_claro()
        if cifrados:
            logger.info("Perfiles de adoptante cifrados al arrancar: %d.", cifrados)
    return dados._replace(
        # DT-06: con PostgreSQL el límite vale para todos los procesos y sobrevive a un reinicio.
        limite_intentos=dados.limite_intentos or LimiteIntentos(
            RepositorioIntentosPostgres(motor)),
        repositorio_rescates=dados.repositorio_rescates or RepositorioRescatesPostgres(motor),
        # #63: los avisos viven en la misma base que los reportes (la confirmación los guarda).
        repositorio_avisos=dados.repositorio_avisos or RepositorioAvisosPostgres(motor),
        repositorio_refugios=dados.repositorio_refugios or RepositorioRefugiosPostgres(motor),
        cifrador=cifrador,
        repositorio_adopciones=adopciones,
        repositorio_bitacora=dados.repositorio_bitacora or RepositorioBitacoraPostgres(motor),
        repositorio_fotos=dados.repositorio_fotos or RepositorioFotosPostgres(motor),
        repositorio_videos=dados.repositorio_videos or RepositorioVideosPostgres(motor),
        repositorio_piloto=dados.repositorio_piloto or RepositorioPilotoPostgres(motor))


def _en_memoria(dados: Repositorios, _motor: None) -> Repositorios:
    refugios = dados.repositorio_refugios
    if refugios is None:
        # #67 (RF-14): arranca con el refugio de los cupos (id 1), como la migración 0002.
        demo = dados.repositorio_cupos.refugio()
        refugios = RepositorioRefugiosEnMemoria(
            [Refugio(demo.nombre, demo.capacidad, demo.ocupados, id=1)])
    return dados._replace(
        limite_intentos=dados.limite_intentos or LimiteIntentos(RepositorioIntentosEnMemoria()),
        repositorio_rescates=dados.repositorio_rescates or RepositorioRescatesEnMemoria(),
        repositorio_avisos=(dados.repositorio_avisos
                            or getattr(dados.repositorio, "avisos", None)
                            or RepositorioAvisosEnMemoria()),
        repositorio_refugios=refugios,
        repositorio_adopciones=(dados.repositorio_adopciones
                                or RepositorioAdopcionesEnMemoria(dados.repositorio_cupos)),
        repositorio_bitacora=dados.repositorio_bitacora or RepositorioBitacoraEnMemoria(),
        repositorio_fotos=dados.repositorio_fotos or RepositorioFotosEnMemoria(),
        repositorio_videos=dados.repositorio_videos or RepositorioVideosEnMemoria(),
        repositorio_piloto=dados.repositorio_piloto or RepositorioPilotoEnMemoria())


def armar_video(motor: Engine | None, token_video: str | None, directorio_videos: str | None):
    """#125: el token del trabajador local y dónde se guardan los videos y sus vistas. Sin
    token, el análisis queda apagado (manda el texto)."""
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
    return token_video, almacen_videos, almacen_vistas


def cargar_demo_al_arrancar(motor: Engine | None, contrasena: str | None,
                            dependencias: Dependencias) -> None:
    """#109: datos de demostración. Con PostgreSQL se leen del entorno (Render no tiene
    consola); las pruebas pasan la contraseña. Un error aquí no impide que la API arranque."""
    if motor is not None:
        contrasena = contrasena or cargar_ajustes_demo().contrasena_si_activa()
    if not contrasena:
        return
    try:
        cargar_demo(dependencias, contrasena)
    except Exception:
        logger.exception("No se pudieron cargar los datos de demostración.")
