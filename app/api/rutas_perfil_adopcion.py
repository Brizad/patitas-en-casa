"""Perfil de adopción del animal y colección de «Adoptar» (#508, parte 2).

- Coordinador y veterinario editan estadísticas (1 a 5) y habilidades del catálogo fijo.
- Solo el veterinario edita la salud para la adopción (sí, no o sin dato).
- La colección es pública como el catálogo: cuántos esperan, cuántos encontraron hogar y los
  8 adoptados más recientes (solo animales: nada del adoptante, RN-14).
"""
from __future__ import annotations

from dataclasses import replace
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.adopciones.modelos import Publicacion
from app.adopciones.perfil import HABILIDADES, ORIGEN, a_cien, nivel, perfil_de_adopcion
from app.api.comun import Contexto, fecha_utc
from app.api.rutas_adopciones import _exigir, _publicacion
from app.api.seguridad import exigir_rol
from app.dominio.modelos import Rol, Usuario

ADOPTADOS_EN_LA_COLECCION = 8

Estadistica = Annotated[int | None, Field(default=None, ge=1, le=5)]


class Estadisticas(BaseModel):
    energia: Estadistica = None
    carino: Estadistica = None
    juego: Estadistica = None
    paciencia: Estadistica = None


class PerfilEntrada(BaseModel):
    estadisticas: Estadisticas
    habilidades: list[Literal[HABILIDADES]] = Field(default_factory=list,  # type: ignore[valid-type]
                                                    max_length=len(HABILIDADES))


class SaludEntrada(BaseModel):
    vacunas: bool | None = None
    esterilizado: bool | None = None
    desparasitado: bool | None = None


def _del_refugio(ctx: Contexto, animal_id: int, usuario: Usuario) -> Publicacion:
    _exigir(ctx.fichas_de(usuario).animal(animal_id), "No hay ese animal en tu refugio.")
    return _exigir(ctx.repositorio_adopciones.publicacion(animal_id),
                   "Ese animal no está publicado: publícalo primero en Adopciones.")


def _guardar(ctx: Contexto, actual: Publicacion, **cambios) -> dict:
    nueva = replace(actual, **cambios)
    if not ctx.repositorio_adopciones.actualizar_publicacion(nueva):
        raise HTTPException(status_code=409, detail=f"{actual.nombre} ya no está disponible.")
    return {"animal_id": nueva.animal_id, "nombre": nueva.nombre, **perfil_de_adopcion(nueva)}


def _niveles(actual: Publicacion, est: Estadisticas) -> dict:
    """1-5 → 0-100. Si el nivel no cambió, se queda el valor fino de la ficha (por ejemplo, 45)."""
    cambios = {}
    for clave, campo in ORIGEN.items():
        nuevo = getattr(est, clave)
        cambios[campo] = (getattr(actual, campo) if nivel(getattr(actual, campo)) == nuevo
                          else a_cien(nuevo))
    return cambios


def crear_rutas_perfil_adopcion(ctx: Contexto) -> APIRouter:
    rutas = APIRouter()
    equipo = exigir_rol(ctx.dependencia_usuario, Rol.COORDINADOR, Rol.VETERINARIO)

    @rutas.get("/refugio/animales/{animal_id}/perfil-adopcion")
    def perfil_del_animal(animal_id: int, usuario: Usuario = equipo):
        actual = _del_refugio(ctx, animal_id, usuario)
        return {"animal_id": animal_id, "nombre": actual.nombre, **perfil_de_adopcion(actual),
                "catalogo_habilidades": list(HABILIDADES)}

    @rutas.put("/refugio/animales/{animal_id}/perfil-adopcion")
    def editar_perfil(animal_id: int, datos: PerfilEntrada, usuario: Usuario = equipo):
        """Coordinador o veterinario: estadísticas y habilidades (no la salud)."""
        actual = _del_refugio(ctx, animal_id, usuario)
        return _guardar(ctx, actual, **_niveles(actual, datos.estadisticas),
                        habilidades=list(dict.fromkeys(datos.habilidades)))

    @rutas.put("/refugio/animales/{animal_id}/salud-adopcion")
    def editar_salud(animal_id: int, datos: SaludEntrada, veterinario: Usuario = ctx.veterinaria):
        """Solo el veterinario: vacunas, esterilización y desparasitación."""
        return _guardar(ctx, _del_refugio(ctx, animal_id, veterinario), **datos.model_dump())

    @rutas.get("/adopciones/coleccion")
    def coleccion():
        """Público, como el catálogo: contador real y los adoptados más recientes (RN-14)."""
        con_foto = ctx.repositorio_fotos.con_foto()
        adoptadas = ctx.repositorio_adopciones.adoptadas()
        return {"esperando": len(ctx.repositorio_adopciones.disponibles()),
                "adoptados_total": len(adoptadas),
                "adoptados": [{**_publicacion(p, con_foto), "adoptado_en": fecha_utc(cuando)}
                              for p, cuando in adoptadas[:ADOPTADOS_EN_LA_COLECCION]]}

    return rutas
