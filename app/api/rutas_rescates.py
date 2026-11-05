"""Rutas del rescatista: disponibilidad, zona, ofertas, rescate en curso, pasos y Mis rescates
(HU-06, RN-08, RF-05, RF-15, RF-21, RF-22) (DT-13, #267)."""
from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
)
from pydantic import BaseModel, Field

from app.api.comun import Contexto, fecha_utc
from app.dominio.modelos import (
    EstadoRescate,
    Reporte,
    Rescate,
    ResultadoRescate,
    Usuario,
)
from app.rescates.servicio import (
    PasoInvalido,
    RescateNoOfrecido,
)

Comuna = Annotated[int, Field(ge=1, le=10)]


class ZonaEntrada(BaseModel):
    """Comunas que cubre el rescatista; lista vacía = toda la ciudad (#46)."""

    comunas: list[Comuna] = Field(max_length=10)


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


# C901: como en crear_app, mccabe suma las rutas anidadas; cada una es sencilla.
def crear_rutas_rescates(ctx: Contexto) -> APIRouter:  # noqa: C901
    rutas = APIRouter()
    avisar_al_ciudadano = ctx.avisar_al_ciudadano
    repositorio_rescates = ctx.repositorio_rescates
    rescates = ctx.rescates
    rescatista_actual = ctx.rescatista_actual

    # --- HU-06: rescatistas (RF-05, RF-15, RN-08) --------------------------------------

    @rutas.put("/rescatistas/yo/disponibilidad")
    def cambiar_disponibilidad(datos: DisponibilidadEntrada,
                               rescatista: Usuario = rescatista_actual):
        rescates.cambiar_disponibilidad(rescatista, datos.disponible)
        return {"disponible": datos.disponible}

    @rutas.put("/rescatistas/yo/zona")
    def cambiar_zona(datos: ZonaEntrada, rescatista: Usuario = rescatista_actual):
        """#46: comunas de Cúcuta que cubre; lista vacía = toda la ciudad."""
        comunas = frozenset(datos.comunas)
        rescates.cambiar_zona(rescatista, comunas)
        return {"comunas": sorted(comunas)}

    @rutas.get("/rescatistas/yo")
    def mi_estado_de_rescatista(rescatista: Usuario = rescatista_actual):
        return {"disponible": rescates.esta_disponible(rescatista),
                "comunas": sorted(rescates.zona(rescatista))}

    @rutas.get("/rescates/ofertas")
    def ofertas_de_rescate(rescatista: Usuario = rescatista_actual):
        """Solo la comuna (ubicación aproximada); la dirección exacta se muestra al aceptar.
        «escalado»: nadie lo aceptó a tiempo y se ofrece en toda la ciudad (RF-23)."""
        escalados = rescates.escalados()
        return [{"codigo": r.codigo, "prioridad": r.prioridad.value,
                 "descripcion": r.descripcion, "comuna": r.ubicacion.comuna,
                 "escalado": r.codigo in escalados,
                 "esperando_desde": fecha_utc(r.creado_en)}
                for r in rescates.ofertas(rescatista)]

    @rutas.get("/rescates/mio")
    def mi_rescate(rescatista: Usuario = rescatista_actual):
        actual = rescates.mio(rescatista)
        return None if actual is None else _rescate(*actual)

    @rutas.get("/rescates/historial")
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

    @rutas.post("/rescates/{codigo}/aceptar")
    def aceptar_rescate(codigo: str, rescatista: Usuario = rescatista_actual):
        return _rescate(*_paso(rescates.aceptar, rescatista, codigo.upper()))

    @rutas.post("/rescates/{codigo}/llegue")
    def llegue_al_sitio(codigo: str, rescatista: Usuario = rescatista_actual):
        _paso(rescates.llegue, rescatista, codigo.upper())
        return {"codigo": codigo.upper(), "estado": "en_sitio"}

    @rutas.post("/rescates/{codigo}/liberar")
    def liberar_rescate(codigo: str, rescatista: Usuario = rescatista_actual):
        _paso(rescates.liberar, rescatista, codigo.upper())
        return {"codigo": codigo.upper(), "estado": "liberado"}

    @rutas.post("/rescates/{codigo}/resultado")
    def resultado_del_rescate(codigo: str, datos: ResultadoEntrada,
                              rescatista: Usuario = rescatista_actual):
        _paso(rescates.registrar_resultado, rescatista, codigo.upper(), datos.resultado)
        if datos.resultado in (ResultadoRescate.TRASLADADO, ResultadoRescate.ATENDIDO_EN_SITIO):
            avisar_al_ciudadano(codigo.upper(), (
                f"un rescatista ya atendió a tu animal del reporte {codigo.upper()}. "
                "Consulta cómo sigue con tu código en la página de seguimiento."))
        return {"codigo": codigo.upper(), "estado": "atendido",
                "resultado": datos.resultado.value}

    return rutas
