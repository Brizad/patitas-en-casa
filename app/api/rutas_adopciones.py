"""Rutas de adopción: adoptante, catálogo, fotos, recomendaciones y gestión del refugio (RF-08 a
RF-10, RF-25 a RF-29) (DT-13, #267)."""
from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.adopciones.compatibilidad import Compatibilidad, recomendar
from app.adopciones.fotos import MAX_BYTES as MAX_BYTES_FOTO
from app.adopciones.fotos import (
    FotoInvalida,
    tipo_de_imagen,
)
from app.adopciones.modelos import (
    Energia,
    PerfilAdoptante,
    Publicacion,
    Tamano,
    Vivienda,
)
from app.adopciones.servicio import (
    AnimalNoDisponible,
    PerfilIncompleto,
    SolicitudRepetida,
)
from app.api.comun import Contexto, fecha_utc
from app.api.comun import cambiar as _cambio
from app.dominio.modelos import (
    Rol,
    Usuario,
)
from app.usuarios.contrasenas import ContrasenaInvalida
from app.usuarios.intentos import (
    clave_registro,
)
from app.usuarios.repositorio import CorreoDuplicado
from app.usuarios.servicio import (
    normalizar_correo,
)

# DT-09 (#149): igual si el correo es nuevo o ya tenía cuenta.
MENSAJE_REGISTRO = ("Listo. Si este correo no tenía cuenta, ya puedes entrar con él y tu "
                    "contraseña. Si ya tenía una, entra con tu contraseña de siempre.")


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


def _publicacion(p: Publicacion, con_foto: set[int] = frozenset()) -> dict:
    foto = f"/adopciones/animales/{p.animal_id}/foto" if p.animal_id in con_foto else None
    return {"foto": foto,"animal_id": p.animal_id, "nombre": p.nombre, "especie": p.especie,
            "descripcion": p.descripcion, "tamano": p.tamano.value, "energia": p.energia.value,
            "edad_meses": p.edad_meses, "apto_ninos": p.apto_ninos,
            "apto_otros_animales": p.apto_otros_animales, "necesita_patio": p.necesita_patio,
            "estado": p.estado.value, "publicado_en": fecha_utc(p.publicado_en)}


class SolicitudEntrada(BaseModel):
    animal_id: int
    mensaje: str = Field(default="", max_length=1000)


def _compatibilidad(c: Compatibilidad) -> dict:
    return {"puntaje": c.puntaje, "razones": c.razones, "alertas": c.alertas,
            "restricciones": c.restricciones}


# C901: como en crear_app, mccabe suma las rutas anidadas; cada una es sencilla.
def crear_rutas_adopciones(ctx: Contexto) -> APIRouter:  # noqa: C901
    rutas = APIRouter()
    adopciones = ctx.adopciones
    adoptante_actual = ctx.adoptante_actual
    coordinacion = ctx.coordinacion
    fichas_de = ctx.fichas_de
    limite_intentos = ctx.limite_intentos
    repositorio_adopciones = ctx.repositorio_adopciones
    repositorio_fotos = ctx.repositorio_fotos
    usuarios = ctx.usuarios

    # --- Fase 3 (#85): adoptante (RF-08) ---------------------------------------------

    @rutas.post("/adoptantes", status_code=201)
    def registrar_adoptante(datos: RegistroAdoptante, peticion: Request):
        """Público, como el reporte: el adoptante no es personal y crea su propia cuenta.
        El rol siempre es adoptante; nadie puede registrarse como personal por aquí.

        DT-09 (#149): máximo REGISTROS_MAXIMOS_POR_IP intentos por IP en la ventana (429), y
        la misma respuesta exista o no el correo: así nadie averigua quién tiene cuenta."""
        clave = clave_registro(peticion.client.host if peticion.client else "desconocida")
        espera = limite_intentos.segundos_de_bloqueo([clave])
        if espera:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados registros desde esta conexión. Intenta en {espera} segundos.",
                headers={"Retry-After": str(espera)})
        limite_intentos.registrar_fallo([clave])
        if not datos.autoriza_datos:
            raise HTTPException(status_code=422, detail=(
                "Para crear la cuenta debes autorizar el tratamiento de tus datos "
                "(Ley 1581 de 2012)."))
        try:
            usuarios.registrar(datos.correo, datos.nombre, Rol.ADOPTANTE, datos.contrasena)
        except CorreoDuplicado:
            # La cuenta existente no cambia. El hash ya se calculó antes de fallar, así que
            # tampoco el tiempo de respuesta delata el correo.
            pass
        except (ContrasenaInvalida, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"correo": normalizar_correo(datos.correo), "rol": Rol.ADOPTANTE.value,
                "mensaje": MENSAJE_REGISTRO}

    @rutas.get("/adoptantes/yo/perfil")
    def mi_perfil(adoptante: Usuario = adoptante_actual):
        perfil = repositorio_adopciones.perfil(adoptante.correo)
        if perfil is None:
            raise HTTPException(status_code=404, detail="Aún no has llenado tu perfil.")
        return {**{k: v for k, v in vars(perfil).items() if k != "actualizado_en"},
                "actualizado_en": fecha_utc(perfil.actualizado_en)}

    @rutas.put("/adoptantes/yo/perfil")
    def guardar_mi_perfil(datos: PerfilEntrada, peticion: Request,
                          adoptante: Usuario = adoptante_actual):
        antes = repositorio_adopciones.perfil(adoptante.correo)
        nuevos = datos.model_dump()
        cambiados = sorted(k for k, v in nuevos.items()
                           if antes is None or getattr(antes, k) != v)
        _cambio(peticion, None if antes is None else {"campos": cambiados},
                {"campos": cambiados})
        repositorio_adopciones.guardar_perfil(
            PerfilAdoptante(correo=adoptante.correo, **datos.model_dump()))
        return {"correo": adoptante.correo, "guardado": True}

    @rutas.post("/refugio/animales/{animal_id}/publicacion", status_code=201)
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

    @rutas.get("/adopciones/animales")
    def catalogo_de_adopcion():
        """Público: animales disponibles. Sin datos del refugio ni de personas (RN-14)."""
        con_foto = repositorio_fotos.con_foto()
        return [_publicacion(p, con_foto) for p in repositorio_adopciones.disponibles()]

    @rutas.get("/adopciones/animales/{animal_id}/foto")
    def foto_del_animal(animal_id: int):
        """Pública, como el catálogo. Se envía con el tipo verificado y nosniff: el navegador
        no intenta adivinar otro tipo (no se puede colar un HTML como imagen)."""
        foto = repositorio_fotos.foto(animal_id)
        if foto is None:
            raise HTTPException(status_code=404, detail="Este animal no tiene foto.")
        return Response(foto[1], media_type=foto[0], headers={
            "X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=3600"})

    @rutas.post("/refugio/animales/{animal_id}/foto", status_code=201)
    async def subir_foto(animal_id: int, foto: Annotated[UploadFile, File()],
                         coordinador: Usuario = coordinacion):
        """RF-25: foto del animal de su refugio (JPEG, PNG o WebP de hasta 300 KB)."""
        if fichas_de(coordinador).animal(animal_id) is None:
            raise HTTPException(status_code=404, detail="No hay ese animal en tu refugio.")
        datos = await foto.read(MAX_BYTES_FOTO + 1)  # no lee más de lo permitido
        try:
            tipo = tipo_de_imagen(datos)
        except FotoInvalida as error:
            raise HTTPException(status_code=413 if "KB" in str(error) else 415,
                                detail=str(error)) from error
        await run_in_threadpool(repositorio_fotos.guardar, animal_id, tipo, datos)
        return {"foto": f"/adopciones/animales/{animal_id}/foto", "tipo": tipo}

    @rutas.get("/adopciones/recomendaciones")
    def recomendaciones(adoptante: Usuario = adoptante_actual):
        """RF-09: animales disponibles ordenados por compatibilidad con SU hogar, con puntaje
        y 3 razones. Los que tienen una restricción dura (RN-05) no aparecen."""
        perfil = repositorio_adopciones.perfil(adoptante.correo)
        if perfil is None:
            raise HTTPException(status_code=422, detail="Llena tu perfil para ver "
                                "recomendaciones.")
        return [{**_publicacion(a), **_compatibilidad(c)}
                for a, c in recomendar(perfil, repositorio_adopciones.disponibles())]

    @rutas.post("/adopciones/solicitudes", status_code=201)
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

    @rutas.get("/adopciones/solicitudes/mias")
    def mis_solicitudes(adoptante: Usuario = adoptante_actual):
        return [{"id": s.id, "animal_id": s.animal_id, "estado": s.estado.value,
                 "creada_en": fecha_utc(s.creada_en)}
                for s in repositorio_adopciones.solicitudes() if s.adoptante == adoptante.correo]

    return rutas
