"""Rutas del refugio: ingresos, animales, ficha clínica, egresos y ocupación (RF-06, RF-07, RF-24,
RF-26, RN-04) (DT-13, #267)."""
from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from pydantic import BaseModel, Field

from app.api.comun import Contexto, fecha_utc
from app.api.comun import cambiar as _cambio
from app.cupos.fichas import AnimalNoEncontrado, NotaInvalida, ServicioFichas
from app.cupos.servicio import CupoAgotado
from app.dominio.modelos import (
    Animal,
    Especie,
    MotivoEgreso,
    TipoNota,
    Usuario,
)
from app.reportes.seguimiento import normalizar_codigo


class IngresoEntrada(BaseModel):
    reporte: str | None = None  # si viene, el ciudadano que lo reportó recibe un aviso
    nombre: str
    especie: Especie
    estado_salud: str
    vacunado: bool = False
    esterilizado: bool = False


class EgresoEntrada(BaseModel):
    motivo: MotivoEgreso


class NotaEntrada(BaseModel):
    tipo: TipoNota
    texto: str = Field(max_length=2000)


def _ficha(animal: Animal) -> dict:
    return {"id": animal.id, "nombre": animal.nombre, "especie": animal.especie.value,
            "estado_salud": animal.estado_salud, "vacunado": animal.vacunado,
            "esterilizado": animal.esterilizado, "ingresado_en": fecha_utc(animal.ingresado_en),
            "egresado_en": fecha_utc(animal.egresado_en),
            "motivo_egreso": animal.motivo_egreso.value if animal.motivo_egreso else None}


def _registrar_ingreso(ctx: Contexto, datos: IngresoEntrada, peticion: Request,
                       coordinador: Usuario) -> dict:
    cupos = ctx.cupos_de(coordinador)
    antes = cupos.texto_ocupacion()
    codigo = normalizar_codigo(datos.reporte) if datos.reporte else None
    if codigo and ctx.repositorio.buscar(codigo) is None:
        raise HTTPException(status_code=422, detail="No existe un reporte con ese código.")
    try:
        cupos.registrar_ingreso(Animal(**datos.model_dump(exclude={"reporte"})))
    except CupoAgotado as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if codigo:
        ctx.avisar_al_ciudadano(codigo, (
            f"el animal de tu reporte {codigo} ya ingresó al refugio. "
            "Consulta cómo sigue con tu código en la página de seguimiento."))
    _cambio(peticion, {"ocupacion": antes}, {"ocupacion": cupos.texto_ocupacion()})
    return {"ocupacion": cupos.texto_ocupacion()}


def _animal_o_404(repo, animal_id: int) -> Animal:
    animal = repo.animal(animal_id)
    if animal is None:
        raise HTTPException(status_code=404, detail="No hay ese animal en tu refugio.")
    return animal


def _ficha_clinica(ctx: Contexto, animal_id: int, usuario: Usuario) -> dict:
    repo = ctx.fichas_de(usuario)
    animal = _animal_o_404(repo, animal_id)
    return {**_ficha(animal), "historial": [
        {"tipo": n.tipo.value, "texto": n.texto, "autor": n.autor,
         "registrada_en": fecha_utc(n.registrada_en)} for n in repo.historial(animal_id)]}


def _agregar_nota_clinica(ctx: Contexto, animal_id: int, datos: NotaEntrada,
                          veterinario: Usuario) -> dict:
    try:
        nota = ServicioFichas(ctx.fichas_de(veterinario)).agregar_nota(
            animal_id, veterinario, datos.tipo, datos.texto)
    except AnimalNoEncontrado as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except NotaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"tipo": nota.tipo.value, "texto": nota.texto, "autor": nota.autor,
            "registrada_en": fecha_utc(nota.registrada_en)}


def _registrar_egreso(ctx: Contexto, animal_id: int, datos: EgresoEntrada, peticion: Request,
                      coordinador: Usuario) -> dict:
    repo = ctx.fichas_de(coordinador)
    animal = _animal_o_404(repo, animal_id)
    antes = ctx.cupos_de(coordinador).texto_ocupacion()
    refugio = repo.egresar(animal_id, datos.motivo)
    if refugio is None:
        raise HTTPException(status_code=409, detail=f"{animal.nombre} ya egresó.")
    _cambio(peticion, {"ocupacion": antes, "en_refugio": True},
            {"ocupacion": refugio.texto_ocupacion(), "en_refugio": False,
             "motivo": datos.motivo.value})
    return {"ocupacion": refugio.texto_ocupacion()}


def crear_rutas_refugio(ctx: Contexto) -> APIRouter:
    rutas = APIRouter()
    _rutas_de_ingreso_y_ficha(rutas, ctx)
    _rutas_de_egreso_y_ocupacion(rutas, ctx)
    return rutas


def _rutas_de_ingreso_y_ficha(rutas: APIRouter, ctx: Contexto) -> None:
    coordinacion = ctx.coordinacion
    fichas_de = ctx.fichas_de
    personal = ctx.personal
    veterinaria = ctx.veterinaria

    @rutas.post("/refugio/ingresos", status_code=201)
    def registrar_ingreso(datos: IngresoEntrada, peticion: Request,
                          coordinador: Usuario = coordinacion):
        return _registrar_ingreso(ctx, datos, peticion, coordinador)

    # --- Fase 2 (#75): ficha clínica e historial (RF-06, RF-24) -----------------------

    @rutas.get("/refugio/animales")
    def animales_del_refugio(usuario: Usuario = personal):
        return [_ficha(a) for a in fichas_de(usuario).animales()]

    @rutas.get("/refugio/animales/{animal_id}")
    def ficha_clinica(animal_id: int, usuario: Usuario = personal):
        return _ficha_clinica(ctx, animal_id, usuario)

    @rutas.post("/refugio/animales/{animal_id}/historial", status_code=201)
    def agregar_nota_clinica(animal_id: int, datos: NotaEntrada,
                             veterinario: Usuario = veterinaria):
        return _agregar_nota_clinica(ctx, animal_id, datos, veterinario)


def _rutas_de_egreso_y_ocupacion(rutas: APIRouter, ctx: Contexto) -> None:
    coordinacion = ctx.coordinacion
    cupos_de = ctx.cupos_de
    personal = ctx.personal

    @rutas.post("/refugio/animales/{animal_id}/egreso")
    def registrar_egreso(animal_id: int, datos: EgresoEntrada, peticion: Request,
                         coordinador: Usuario = coordinacion):
        """RF-26: como el ingreso, es del coordinador. 404 si no está en su refugio y 409 si
        ya egresó (el cupo no se libera dos veces)."""
        return _registrar_egreso(ctx, animal_id, datos, peticion, coordinador)

    @rutas.get("/refugio/ocupacion")
    def ocupacion(usuario: Usuario = personal):
        cupos = cupos_de(usuario)
        return {"ocupacion": cupos.texto_ocupacion(),
                "porcentaje": round(cupos.porcentaje_ocupacion() * 100, 1)}
