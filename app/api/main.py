"""API REST del MVP de Patitas en Casa (FastAPI).

Se inicia con: uvicorn --factory app.api.main:crear_app
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import Engine, create_engine

from app.ajustes import cargar_ajustes, cargar_ajustes_correo, cargar_ajustes_seguridad
from app.api.seguridad import crear_dependencia_usuario, exigir_rol, no_autenticado
from app.bd.migraciones import verificar_migraciones
from app.cupos.repositorio import RepositorioCupos
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.cupos.servicio import CupoAgotado, Notificador, ServicioCupos
from app.dominio.modelos import Animal, Especie, Rol, Ubicacion, Usuario
from app.notificaciones.correo import crear_notificador
from app.reportes.repositorio import RepositorioReportes
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.reportes.servicio import ReporteInvalido, ServicioReportes
from app.seguridad.tokens import EmisorTokens
from app.triaje.servicio import ServicioTriaje, ordenar_cola
from app.usuarios.repositorio import RepositorioUsuarios
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios

# Pueden usar /cola y /refugio. Públicos (RF-01): POST /reportes y GET /reportes/{codigo}.
ROLES_PERSONAL = (Rol.VETERINARIO, Rol.COORDINADOR)


class ReporteEntrada(BaseModel):
    descripcion: str
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = None
    video_segundos: int | None = Field(default=None, ge=0)
    video_mb: float | None = Field(default=None, ge=0)


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
              notificador: Notificador | None = None) -> FastAPI:
    """Sin argumentos usa PostgreSQL, la clave JWT y el SMTP del .env; las pruebas inyectan
    dobles."""
    emisor_tokens = emisor_tokens or emisor_desde_entorno()
    notificador = notificador or crear_notificador(cargar_ajustes_correo())
    motor = None
    if repositorio is None or repositorio_cupos is None or repositorio_usuarios is None:
        motor = motor_desde_entorno()
        repositorio = repositorio or RepositorioPostgres(motor)
        repositorio_cupos = repositorio_cupos or RepositorioCuposPostgres.primer_refugio(motor)
        repositorio_usuarios = repositorio_usuarios or RepositorioUsuariosPostgres(motor)
    usuarios = ServicioUsuarios(repositorio_usuarios)
    dependencia_usuario = crear_dependencia_usuario(repositorio_usuarios, emisor_tokens)
    usuario_actual = Depends(dependencia_usuario)
    # DT-02: el personal se identifica con su token; X-Rol ya no existe.
    personal = exigir_rol(dependencia_usuario, *ROLES_PERSONAL)

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if motor is not None:
            motor.dispose()

    app = FastAPI(title="Patitas en Casa", version="0.1.0", lifespan=ciclo_de_vida)
    reportes = ServicioReportes(repositorio, ServicioTriaje())
    cupos = ServicioCupos(repositorio_cupos, notificador)

    @app.post("/auth/token")
    def iniciar_sesion(formulario: Annotated[OAuth2PasswordRequestForm, Depends()]):
        """Inicio de sesión del personal: username = correo (DT-02)."""
        usuario = usuarios.autenticar(formulario.username, formulario.password)
        if usuario is None:
            # Mismo mensaje exista o no el correo: no se revela qué cuentas existen.
            raise no_autenticado("Correo o contraseña incorrectos.")
        return {"access_token": emisor_tokens.emitir(usuario), "token_type": "bearer",
                "expira_en": emisor_tokens.minutos * 60}

    @app.get("/auth/yo")
    def mi_cuenta(usuario: Usuario = usuario_actual):
        return {"correo": usuario.correo, "nombre": usuario.nombre, "rol": usuario.rol.value}

    @app.post("/reportes", status_code=201)
    def crear_reporte(datos: ReporteEntrada):
        ubicacion = Ubicacion(datos.latitud, datos.longitud, datos.direccion)
        try:
            r = reportes.registrar(datos.descripcion, ubicacion,
                                   datos.video_segundos, datos.video_mb)
        except ReporteInvalido as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"codigo": r.codigo, "estado": r.estado.value}

    @app.get("/reportes/{codigo}")
    def estado_reporte(codigo: str):
        r = repositorio.buscar(codigo.upper())
        if r is None:
            raise HTTPException(status_code=404, detail="Código de seguimiento no encontrado.")
        return {"codigo": r.codigo, "estado": r.estado.value}

    @app.get("/cola", dependencies=[personal])
    def cola():
        return [
            {"codigo": r.codigo, "prioridad": r.prioridad.value, "estado": r.estado.value,
             "confianza": r.confianza, "evidencias": r.evidencias}
            for r in ordenar_cola(repositorio.todos())
        ]

    @app.post("/refugio/ingresos", status_code=201, dependencies=[personal])
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
