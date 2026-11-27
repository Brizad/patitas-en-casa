"""Rutas del rescatista: disponibilidad, zona, ofertas, rescate en curso, pasos y Mis rescates
(HU-06, RN-08, RF-05, RF-15, RF-21, RF-22) (DT-13, #267)."""
from __future__ import annotations

from datetime import UTC, datetime
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
from app.reportes import orden
from app.rescates.servicio import (
    PasoInvalido,
    RescateNoOfrecido,
    SinPermiso,
)
from app.rescates.simulacion import Simulaciones

Comuna = Annotated[int, Field(ge=1, le=10)]


class ZonaEntrada(BaseModel):
    """Comunas que cubre el rescatista; lista vacía = toda la ciudad (#46)."""

    comunas: list[Comuna] = Field(max_length=10)


class DisponibilidadEntrada(BaseModel):
    disponible: bool


class ResultadoEntrada(BaseModel):
    resultado: ResultadoRescate


class UbicacionEntrada(BaseModel):
    """#498: posición del rescatista en camino (la envía watchPosition cada 10–15 s)."""

    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


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


def _aproximada(valor: float | None) -> float | None:
    """#496: unos 110 m de precisión, para el mapa y la distancia antes de aceptar (la
    dirección y el punto exacto siguen siendo solo para quien acepta)."""
    return None if valor is None else round(valor, 3)


def _ofertas(ctx: Contexto, rescatista: Usuario) -> list[dict]:
    escalados = ctx.rescates.escalados()
    ahora = datetime.now(UTC)
    filas = []
    for r in ctx.rescates.ofertas(rescatista):  # ya en el orden único (#496)
        decisiones = ctx.repositorio.decisiones(r.codigo)
        # Último avance: la confirmación del veterinario (desde ahí espera rescatista).
        avance = decisiones[-1].decidido_en if decisiones else r.creado_en
        filas.append({
            "codigo": r.codigo, "prioridad": r.prioridad.value, "nivel": orden.nivel(r.prioridad),
            "descripcion": r.descripcion, "comuna": r.ubicacion.comuna,
            "escalado": r.codigo in escalados, "esperando_desde": fecha_utc(r.creado_en),
            "atrasado": orden.atrasado(avance, ahora),
            "especie": orden.especie_mencionada(r.descripcion),
            "estado_animal": orden.estado_del_animal(r.evidencias, r.descripcion),
            "latitud": _aproximada(r.ubicacion.latitud),
            "longitud": _aproximada(r.ubicacion.longitud)})
    return filas


def _historial(ctx: Contexto, rescatista: Usuario) -> list[dict]:
    return [{"codigo": r.codigo, "aceptado_en": fecha_utc(r.aceptado_en),
             "llego": r.estado in (EstadoRescate.EN_SITIO, EstadoRescate.ATENDIDO),
             "llegada_en": fecha_utc(r.llegada_en) if r.llegada_en else None,
             "resultado": r.resultado.value if r.resultado else None,
             "estado": r.estado.value, "actualizado_en": fecha_utc(r.actualizado_en)}
            for r in ctx.repositorio_rescates.historial_de(rescatista.correo)]


def _paso(accion, *args):
    try:
        return accion(*args)
    except RescateNoOfrecido as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PasoInvalido as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SinPermiso as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


def _registrar_resultado(ctx: Contexto, codigo: str, datos: ResultadoEntrada,
                         rescatista: Usuario) -> dict:
    _paso(ctx.rescates.registrar_resultado, rescatista, codigo.upper(), datos.resultado)
    if datos.resultado in (ResultadoRescate.TRASLADADO, ResultadoRescate.ATENDIDO_EN_SITIO):
        ctx.avisar_al_ciudadano(codigo.upper(), (
            f"un rescatista ya atendió a tu animal del reporte {codigo.upper()}. "
            "Consulta cómo sigue con tu código en la página de seguimiento."))
    return {"codigo": codigo.upper(), "estado": "atendido", "resultado": datos.resultado.value}


def crear_rutas_rescates(ctx: Contexto) -> APIRouter:
    rutas = APIRouter()
    _rutas_del_rescatista(rutas, ctx)
    _rutas_de_los_pasos(rutas, ctx)
    _rutas_de_la_ubicacion(rutas, ctx)
    return rutas


def _rutas_de_la_ubicacion(rutas: APIRouter, ctx: Contexto) -> None:
    """#498: seguimiento del rescatista en el mapa del ciudadano y recorrido de demostración."""
    rescates = ctx.rescates
    rescatista_actual = ctx.rescatista_actual
    simulaciones = Simulaciones(rescates, ctx.repositorio)

    @rutas.put("/rescates/{codigo}/ubicacion")
    def compartir_mi_ubicacion(codigo: str, datos: UbicacionEntrada,
                               rescatista: Usuario = rescatista_actual):
        """Solo el rescatista asignado y solo mientras va en camino (403 / 409). Se guarda SOLO
        la última posición; se borra sola al llegar, atender o liberar el caso."""
        _paso(rescates.compartir_ubicacion, rescatista, codigo.upper(), datos.latitud,
              datos.longitud)
        return {"codigo": codigo.upper(), "compartiendo": True}

    @rutas.delete("/rescates/{codigo}/ubicacion")
    def dejar_de_compartir(codigo: str, rescatista: Usuario = rescatista_actual):
        _paso(rescates.dejar_de_compartir, rescatista, codigo.upper())
        return {"codigo": codigo.upper(), "compartiendo": False}

    @rutas.post("/rescates/{codigo}/simulacion", status_code=202)
    def simular_recorrido(codigo: str, rescatista: Usuario = rescatista_actual):
        """Solo cuentas de demostración (403 para las demás): el servidor mueve la posición
        ~1,5 km hasta el animal y luego marca el caso atendido."""
        segundos = _paso(simulaciones.iniciar, rescatista, codigo.upper())
        return {"codigo": codigo.upper(), "segundos": segundos}


def _rutas_del_rescatista(rutas: APIRouter, ctx: Contexto) -> None:
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
        return _ofertas(ctx, rescatista)

    @rutas.get("/rescates/mio")
    def mi_rescate(rescatista: Usuario = rescatista_actual):
        actual = rescates.mio(rescatista)
        return None if actual is None else _rescate(*actual)

    @rutas.get("/rescates/historial")
    def historial_de_rescates(rescatista: Usuario = rescatista_actual):
        """Mis rescates: los que aceptó, del más reciente al más viejo. Solo fechas y estados:
        la dirección exacta se muestra únicamente en el rescate en curso."""
        return _historial(ctx, rescatista)


def _rutas_de_los_pasos(rutas: APIRouter, ctx: Contexto) -> None:
    rescates = ctx.rescates
    rescatista_actual = ctx.rescatista_actual

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
        return _registrar_resultado(ctx, codigo, datos, rescatista)
