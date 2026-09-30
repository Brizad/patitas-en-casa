"""API REST del MVP de Patitas en Casa (FastAPI)."""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.cupos.servicio import CupoAgotado, ServicioCupos
from app.dominio.modelos import Animal, Especie, Refugio, Ubicacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.servicio import ReporteInvalido, ServicioReportes
from app.triaje.servicio import ServicioTriaje, ordenar_cola

ROLES_COLA = {"veterinario", "coordinador"}


class NotificadorConsola:
    def enviar(self, destinatario: str, mensaje: str) -> None:
        print(f"[notificación a {destinatario}] {mensaje}")


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


def crear_app() -> FastAPI:
    app = FastAPI(title="Patitas en Casa", version="0.1.0")
    repositorio = RepositorioEnMemoria()
    reportes = ServicioReportes(repositorio, ServicioTriaje())
    cupos = ServicioCupos(Refugio("Refugio demo Cúcuta", capacidad=40, ocupados=0),
                          NotificadorConsola())

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

    @app.get("/cola")
    def cola(x_rol: str = Header(default="")):
        if x_rol not in ROLES_COLA:
            raise HTTPException(status_code=403, detail="Solo veterinarios y coordinadores.")
        return [
            {"codigo": r.codigo, "prioridad": r.prioridad.value, "estado": r.estado.value,
             "confianza": r.confianza, "evidencias": r.evidencias}
            for r in ordenar_cola(repositorio.todos())
        ]

    @app.post("/refugio/ingresos", status_code=201)
    def registrar_ingreso(datos: IngresoEntrada):
        try:
            cupos.registrar_ingreso(Animal(**datos.model_dump()))
        except CupoAgotado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"ocupacion": cupos.texto_ocupacion()}

    @app.get("/refugio/ocupacion")
    def ocupacion():
        return {"ocupacion": cupos.texto_ocupacion(),
                "porcentaje": round(cupos.porcentaje_ocupacion() * 100, 1)}

    return app


app = crear_app()
