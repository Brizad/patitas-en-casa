"""Rutas de adopción: adoptante, catálogo, fotos, recomendaciones y gestión del refugio (RF-08 a
RF-10, RF-25 a RF-29) (DT-13, #267)."""
from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field, StringConstraints
from starlette.concurrency import run_in_threadpool

from app import config
from app.adopciones.asignacion import asignar
from app.adopciones.compatibilidad import Compatibilidad, calcular, recomendar
from app.adopciones.compromiso import lineas_compromiso
from app.adopciones.fotos import MAX_BYTES as MAX_BYTES_FOTO
from app.adopciones.fotos import (
    FotoInvalida,
    tipo_de_imagen,
)
from app.adopciones.modelos import (
    Energia,
    EstadoPublicacion,
    EstadoSolicitud,
    PerfilAdoptante,
    Publicacion,
    Seguimiento,
    Tamano,
    Vivienda,
)
from app.adopciones.servicio import (
    AnimalNoDisponible,
    PerfilIncompleto,
    RazonInvalida,
    RestriccionDura,
    SeguimientoNoValido,
    SinCupoParaDevolucion,
    SolicitudNoEncontrada,
    SolicitudRepetida,
    SolicitudYaDecidida,
)
from app.api.comun import Contexto, fecha_utc
from app.api.comun import cambiar as _cambio
from app.api.seguridad import exigir_rol
from app.documentos.pdf import generar_pdf
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
logger = logging.getLogger("app.api.main")  # el mismo de antes: los logs no cambian
AVISO_REGISTRO_DUPLICADO = (
    "Patitas en Casa: alguien intentó crear una cuenta de adoptante con este correo. Tu cuenta "
    "no cambió. Si fuiste tú, entra con tu contraseña de siempre; si no, puedes ignorar este "
    "mensaje.")
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


Nivel = Annotated[int | None, Field(default=None, ge=0, le=100)]
Peso = Annotated[float | None, Field(default=None, gt=0, le=150)]
Etiqueta = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class PublicacionEntrada(BaseModel):
    descripcion: str = Field(min_length=20, max_length=1000)
    tamano: Tamano
    energia: Energia
    edad_meses: int = Field(ge=0, le=360)
    apto_ninos: bool
    apto_otros_animales: bool
    necesita_patio: bool
    # #422: ficha «Elige a tu compañero», opcional y solo para mostrar (no cambia RF-09).
    carino: Nivel = None
    energia_nivel: Nivel = None
    juego: Nivel = None
    calma: Nivel = None
    etiquetas: list[Etiqueta] = Field(default_factory=list, max_length=3)
    peso_kg: Peso = None
    peso_adulto_kg: Peso = None


def _publicacion(p: Publicacion, con_foto: set[int] = frozenset()) -> dict:
    foto = f"/adopciones/animales/{p.animal_id}/foto" if p.animal_id in con_foto else None
    return {"foto": foto,"animal_id": p.animal_id, "nombre": p.nombre, "especie": p.especie,
            "descripcion": p.descripcion, "tamano": p.tamano.value, "energia": p.energia.value,
            "edad_meses": p.edad_meses, "apto_ninos": p.apto_ninos,
            "apto_otros_animales": p.apto_otros_animales, "necesita_patio": p.necesita_patio,
            "estado": p.estado.value, "publicado_en": fecha_utc(p.publicado_en),
            "carino": p.carino, "energia_nivel": p.energia_nivel, "juego": p.juego,
            "calma": p.calma, "etiquetas": list(p.etiquetas), "peso_kg": p.peso_kg,
            "peso_adulto_kg": p.peso_adulto_kg}


class SolicitudEntrada(BaseModel):
    animal_id: int
    mensaje: str = Field(default="", max_length=1000)


def _compatibilidad(c: Compatibilidad) -> dict:
    return {"puntaje": c.puntaje, "razones": c.razones, "alertas": c.alertas,
            "restricciones": c.restricciones}


class NotaSolicitudEntrada(BaseModel):
    texto: str = Field(max_length=1000)  # nota de la visita o motivo de la devolución


class DecisionEntrada(BaseModel):
    aprobar: bool
    razon: str | None = Field(default=None, max_length=1000)  # obligatoria al rechazar


class SeguimientoEntrada(BaseModel):
    nota: str = Field(max_length=2000)


def _seguimiento(x: Seguimiento, ahora: datetime) -> dict:
    return {"id": x.id, "dia": x.dia, "programado_para": fecha_utc(x.programado_para),
            "realizado_en": fecha_utc(x.realizado_en), "nota": x.nota,
            "registrado_por": x.registrado_por,
            # Vencido: ya pasó la fecha y nadie lo registró (aparece primero en la lista).
            "vencido": x.realizado_en is None and x.programado_para < ahora}


# --- Casos de uso de las rutas (#4c): la lógica vive aquí, fuera de la fábrica, para que cada
# función se lea y se mida sola (Ruff C901 ≤ 10). Las rutas de abajo solo delegan.

def _traducir(errores: dict[type[Exception], int], funcion, *argumentos):
    """Ejecuta un caso de uso y convierte sus errores de negocio en la respuesta HTTP."""
    try:
        return funcion(*argumentos)
    except tuple(errores) as error:
        estado = next(e for tipo, e in errores.items() if isinstance(error, tipo))
        raise HTTPException(status_code=estado, detail=str(error)) from error


def _exigir(valor, detalle: str, estado: int = 404):
    """Devuelve «valor» o responde 404 (u otro estado) si no existe."""
    if valor is None:
        raise HTTPException(status_code=estado, detail=detalle)
    return valor


def _registrar_adoptante(ctx: Contexto, datos: RegistroAdoptante, peticion: Request,
                         tareas: BackgroundTasks) -> dict:
    clave = clave_registro(ctx.ip_de(peticion))
    espera = ctx.limite_intentos.segundos_de_bloqueo([clave])
    if espera:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados registros desde esta conexión. Intenta en {espera} segundos.",
            headers={"Retry-After": str(espera)})
    ctx.limite_intentos.registrar_fallo([clave])
    if not datos.autoriza_datos:
        raise HTTPException(status_code=422, detail=(
            "Para crear la cuenta debes autorizar el tratamiento de tus datos "
            "(Ley 1581 de 2012)."))
    try:
        ctx.usuarios.registrar(datos.correo, datos.nombre, Rol.ADOPTANTE, datos.contrasena)
    except CorreoDuplicado:
        # La cuenta existente no cambia. El hash ya se calculó antes de fallar, así que
        # tampoco el tiempo de respuesta delata el correo.
        if config.AVISAR_REGISTRO_DUPLICADO:  # P-12: apagado por defecto
            tareas.add_task(_avisar_registro_duplicado, ctx.notificador,
                            normalizar_correo(datos.correo))
    except (ContrasenaInvalida, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"correo": normalizar_correo(datos.correo), "rol": Rol.ADOPTANTE.value,
            "mensaje": MENSAJE_REGISTRO}


def _avisar_registro_duplicado(notificador, correo: str) -> None:
    """P-12: corre después de responder (BackgroundTasks). Una falla queda en el log."""
    try:
        notificador.enviar(correo, AVISO_REGISTRO_DUPLICADO)
    except Exception:
        logger.exception("No se pudo avisar al dueño de un correo ya registrado.")


def _guardar_perfil(ctx: Contexto, datos: PerfilEntrada, peticion: Request,
                    adoptante: Usuario) -> dict:
    antes = ctx.repositorio_adopciones.perfil(adoptante.correo)
    nuevos = datos.model_dump()
    cambiados = sorted(k for k, v in nuevos.items()
                       if antes is None or getattr(antes, k) != v)
    _cambio(peticion, None if antes is None else {"campos": cambiados},
            {"campos": cambiados})
    ctx.repositorio_adopciones.guardar_perfil(
        PerfilAdoptante(correo=adoptante.correo, **datos.model_dump()))
    return {"correo": adoptante.correo, "guardado": True}


def _publicar_animal(ctx: Contexto, animal_id: int, datos: PublicacionEntrada,
                     coordinador: Usuario) -> dict:
    animal = _exigir(ctx.fichas_de(coordinador).animal(animal_id),
                     "No hay ese animal en tu refugio.")
    if animal.egresado_en is not None:
        raise HTTPException(status_code=409, detail=f"{animal.nombre} ya egresó.")
    publicacion = Publicacion(animal_id=animal_id, nombre=animal.nombre,
                              especie=animal.especie.value, **datos.model_dump())
    if not ctx.repositorio_adopciones.publicar(publicacion):
        raise HTTPException(status_code=409, detail=f"{animal.nombre} ya está publicado.")
    return _publicacion(publicacion)


def _editar_publicacion(ctx: Contexto, animal_id: int, datos: PublicacionEntrada,
                        coordinador: Usuario) -> dict:
    """#422: corrige una publicación disponible de un animal de su refugio."""
    _exigir(ctx.fichas_de(coordinador).animal(animal_id), "No hay ese animal en tu refugio.")
    actual = _exigir(ctx.repositorio_adopciones.publicacion(animal_id),
                     "Ese animal no está publicado.")
    nueva = replace(actual, **datos.model_dump())
    if not ctx.repositorio_adopciones.actualizar_publicacion(nueva):
        raise HTTPException(status_code=409, detail=f"{actual.nombre} ya no está disponible.")
    return _publicacion(nueva)


def _retirar_publicacion(ctx: Contexto, animal_id: int, coordinador: Usuario) -> dict:
    """#450: saca del catálogo a un animal de su refugio. No borra nada: el animal, su ficha,
    su foto y la publicación quedan; solo deja de mostrarse y de recibir solicitudes."""
    _exigir(ctx.fichas_de(coordinador).animal(animal_id), "No hay ese animal en tu refugio.")
    actual = _exigir(ctx.repositorio_adopciones.publicacion(animal_id),
                     "Ese animal no está publicado.")
    if not ctx.repositorio_adopciones.retirar_publicacion(animal_id):
        raise HTTPException(status_code=409, detail=(
            f"{actual.nombre} no se puede retirar: ya no está disponible o tiene solicitudes "
            "abiertas (recházalas primero)."))
    return {"animal_id": animal_id, "nombre": actual.nombre,
            "estado": EstadoPublicacion.RETIRADA.value}


async def _subir_foto(ctx: Contexto, animal_id: int, foto: UploadFile,
                      coordinador: Usuario) -> dict:
    _exigir(ctx.fichas_de(coordinador).animal(animal_id), "No hay ese animal en tu refugio.")
    datos = await foto.read(MAX_BYTES_FOTO + 1)  # no lee más de lo permitido
    try:
        tipo = tipo_de_imagen(datos)
    except FotoInvalida as error:
        raise HTTPException(status_code=413 if "KB" in str(error) else 415,
                            detail=str(error)) from error
    await run_in_threadpool(ctx.repositorio_fotos.guardar, animal_id, tipo, datos)
    return {"foto": f"/adopciones/animales/{animal_id}/foto", "tipo": tipo}


def _recomendaciones(ctx: Contexto, adoptante: Usuario) -> list[dict]:
    perfil = _exigir(ctx.repositorio_adopciones.perfil(adoptante.correo),
                     "Llena tu perfil para ver recomendaciones.", 422)
    con_foto = ctx.repositorio_fotos.con_foto()  # #422: antes las recomendaciones no la traían
    return [{**_publicacion(a, con_foto), **_compatibilidad(c)}
            for a, c in recomendar(perfil, ctx.repositorio_adopciones.disponibles())]


def _mis_solicitudes(ctx: Contexto, adoptante: Usuario) -> list[dict]:
    """#420 (aditivo): con nombre y especie del animal, que sale del catálogo al adoptarse."""
    repositorio = ctx.repositorio_adopciones
    filas = []
    for s in repositorio.solicitudes():
        if s.adoptante != adoptante.correo:
            continue
        p = repositorio.publicacion(s.animal_id)
        filas.append({"id": s.id, "animal_id": s.animal_id, "estado": s.estado.value,
                      "creada_en": fecha_utc(s.creada_en),
                      "nombre": p.nombre if p else None, "especie": p.especie if p else None})
    return filas


def _solicitudes_del_refugio(ctx: Contexto, coordinador: Usuario) -> list[dict]:
    animales, repositorio = ctx.fichas_de(coordinador), ctx.repositorio_adopciones
    respuesta = []
    for s in repositorio.solicitudes():
        animal = animales.animal(s.animal_id)
        if animal is None:
            continue
        perfil = repositorio.perfil(s.adoptante)
        respuesta.append({
            "id": s.id, "animal_id": s.animal_id, "animal": animal.nombre,
            "adoptante": s.adoptante, "mensaje": s.mensaje, "estado": s.estado.value,
            "razon": s.razon,
            "creada_en": fecha_utc(s.creada_en),
            "perfil": None if perfil is None else {
                k: v for k, v in vars(perfil).items()
                if k not in ("correo", "actualizado_en")},
            # RF-09: ayuda a decidir; la decisión sigue siendo del coordinador (RN-16).
            "compatibilidad": None if perfil is None else _compatibilidad(
                calcular(perfil, repositorio.publicacion(s.animal_id)))})
    return respuesta


def _propuesta_de_jornada(ctx: Contexto, coordinador: Usuario) -> list[dict]:
    animales, repositorio = ctx.fichas_de(coordinador), ctx.repositorio_adopciones
    disponibles = [a for a in repositorio.disponibles()
                   if animales.animal(a.animal_id) is not None]
    pendientes = [s for s in repositorio.solicitudes()
                  if s.estado == EstadoSolicitud.PENDIENTE
                  and animales.animal(s.animal_id) is not None]
    adoptantes = list(dict.fromkeys(s.adoptante for s in pendientes))
    perfiles = [repositorio.perfil(c) for c in adoptantes]
    if not disponibles or not adoptantes:
        return []
    tabla = [[calcular(p, a) for a in disponibles] for p in perfiles]
    pidio = {(s.adoptante, s.animal_id) for s in pendientes}
    return [{"adoptante": adoptantes[i], "animal_id": disponibles[j].animal_id,
             "animal": disponibles[j].nombre, **_compatibilidad(tabla[i][j]),
             "solicito_este_animal": (adoptantes[i], disponibles[j].animal_id) in pidio}
            for i, j in asignar([[c.puntaje for c in fila] for fila in tabla])]


def _solicitud_del_refugio(ctx: Contexto, solicitud_id: int, coordinador: Usuario):
    """La solicitud, solo si es de un animal del refugio del coordinador; si no, 404."""
    s = ctx.repositorio_adopciones.solicitud(solicitud_id)
    if s is None or ctx.fichas_de(coordinador).animal(s.animal_id) is None:
        raise HTTPException(status_code=404, detail="No hay esa solicitud en tu refugio.")
    return s


ERRORES_SOLICITAR = {PerfilIncompleto: 422, AnimalNoDisponible: 404, SolicitudRepetida: 409}
ERRORES_DECIDIR = {SolicitudNoEncontrada: 404, SolicitudYaDecidida: 409, RestriccionDura: 409,
                   RazonInvalida: 422}
ERRORES_VISITA = {SolicitudYaDecidida: 409, RazonInvalida: 422}
ERRORES_DEVOLUCION = {SolicitudYaDecidida: 409, SinCupoParaDevolucion: 409, RazonInvalida: 422}


def _decidir_solicitud(ctx: Contexto, solicitud_id: int, datos: DecisionEntrada,
                       peticion: Request, coordinador: Usuario) -> dict:
    solicitud = _solicitud_del_refugio(ctx, solicitud_id, coordinador)
    s = _traducir(ERRORES_DECIDIR, ctx.adopciones.decidir, coordinador, solicitud_id,
                  datos.aprobar, datos.razon)
    _cambio(peticion, {"estado": solicitud.estado.value}, {"estado": s.estado.value})
    return {"id": s.id, "estado": s.estado.value, "razon": s.razon,
            "seguimientos": [{"dia": x.dia, "programado_para": fecha_utc(x.programado_para)}
                             for x in ctx.repositorio_adopciones.seguimientos(solicitud_id)]}


def _anotar_solicitud(ctx: Contexto, caso_de_uso, errores: dict, clave: str, solicitud_id: int,
                      texto: str, coordinador: Usuario) -> dict:
    """Visita previa (RF-27) o devolución (RF-10): misma forma, distinto caso de uso."""
    _solicitud_del_refugio(ctx, solicitud_id, coordinador)
    s = _traducir(errores, caso_de_uso, coordinador, solicitud_id, texto)
    return {"id": s.id, "estado": s.estado.value, clave: s.razon}


def _seguimientos_del_refugio(ctx: Contexto, coordinador: Usuario) -> list[dict]:
    animales, repositorio = ctx.fichas_de(coordinador), ctx.repositorio_adopciones
    ahora = datetime.now(UTC)
    filas = []
    for s in repositorio.solicitudes():
        animal = animales.animal(s.animal_id)
        if s.estado != EstadoSolicitud.APROBADA or animal is None:
            continue
        for x in repositorio.seguimientos(s.id):
            filas.append({**_seguimiento(x, ahora), "solicitud_id": s.id,
                          "animal": animal.nombre, "adoptante": s.adoptante})
    return sorted(filas, key=lambda f: (f["realizado_en"] is not None,
                                        f["programado_para"]))


def _registrar_seguimiento(ctx: Contexto, seguimiento_id: int, datos: SeguimientoEntrada,
                           coordinador: Usuario) -> dict:
    mios = {f["id"] for f in _seguimientos_del_refugio(ctx, coordinador)}
    if seguimiento_id not in mios:
        raise HTTPException(status_code=404, detail="No hay ese seguimiento en tu refugio.")
    try:
        hecho = ctx.adopciones.registrar_seguimiento(coordinador, seguimiento_id, datos.nota)
    except SeguimientoNoValido as error:
        raise HTTPException(status_code=409 if "registrado" in str(error) else 422,
                            detail=str(error)) from error
    return _seguimiento(hecho, datetime.now(UTC))


def _compromiso_de_adopcion(ctx: Contexto, solicitud_id: int, usuario: Usuario) -> Response:
    repositorio = ctx.repositorio_adopciones
    s = repositorio.solicitud(solicitud_id)
    if s is None or (s.adoptante != usuario.correo if usuario.rol == Rol.ADOPTANTE
                     else ctx.fichas_de(usuario).animal(s.animal_id) is None):
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if s.estado != EstadoSolicitud.APROBADA:
        raise HTTPException(status_code=409,
                            detail="El compromiso existe solo para adopciones aprobadas.")
    adoptante = ctx.repositorio_usuarios.buscar_por_correo(s.adoptante)
    pdf = generar_pdf(lineas_compromiso(
        s, repositorio.publicacion(s.animal_id),
        adoptante.nombre if adoptante else s.adoptante,
        repositorio.seguimientos(s.id),
        ctx.repositorio_refugios.de_animal(s.animal_id)))
    return Response(pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="compromiso-{s.id}.pdf"'})


# --- Rutas: cuatro grupos, en el mismo orden de siempre (el OpenAPI no cambia) ------------

def crear_rutas_adopciones(ctx: Contexto) -> APIRouter:
    rutas = APIRouter()
    _rutas_del_adoptante(rutas, ctx)
    _rutas_del_catalogo(rutas, ctx)
    _rutas_de_solicitudes(rutas, ctx)
    _rutas_de_seguimientos(rutas, ctx)
    return rutas


def _rutas_del_adoptante(rutas: APIRouter, ctx: Contexto) -> None:
    """Fase 3 (#85): adoptante (RF-08)."""
    adoptante_actual = ctx.adoptante_actual

    @rutas.post("/adoptantes", status_code=201)
    def registrar_adoptante(datos: RegistroAdoptante, peticion: Request,
                            tareas: BackgroundTasks):
        """Público, como el reporte: el adoptante no es personal y crea su propia cuenta.
        El rol siempre es adoptante; nadie puede registrarse como personal por aquí.

        DT-09 (#149): máximo REGISTROS_MAXIMOS_POR_IP intentos por IP en la ventana (429), y
        la misma respuesta exista o no el correo: así nadie averigua quién tiene cuenta."""
        return _registrar_adoptante(ctx, datos, peticion, tareas)

    @rutas.get("/adoptantes/yo/perfil")
    def mi_perfil(adoptante: Usuario = adoptante_actual):
        perfil = _exigir(ctx.repositorio_adopciones.perfil(adoptante.correo),
                         "Aún no has llenado tu perfil.")
        return {**{k: v for k, v in vars(perfil).items() if k != "actualizado_en"},
                "actualizado_en": fecha_utc(perfil.actualizado_en)}

    @rutas.put("/adoptantes/yo/perfil")
    def guardar_mi_perfil(datos: PerfilEntrada, peticion: Request,
                          adoptante: Usuario = adoptante_actual):
        return _guardar_perfil(ctx, datos, peticion, adoptante)


def _rutas_del_catalogo(rutas: APIRouter, ctx: Contexto) -> None:
    """Publicación, catálogo público, fotos y recomendaciones (RF-09, RF-25)."""
    adoptante_actual, coordinacion = ctx.adoptante_actual, ctx.coordinacion
    repositorio_fotos = ctx.repositorio_fotos

    @rutas.post("/refugio/animales/{animal_id}/publicacion", status_code=201)
    def publicar_animal(animal_id: int, datos: PublicacionEntrada,
                        coordinador: Usuario = coordinacion):
        """RF-25: el coordinador publica un animal de su refugio que sigue allí."""
        return _publicar_animal(ctx, animal_id, datos, coordinador)

    @rutas.put("/refugio/animales/{animal_id}/publicacion")
    def editar_publicacion(animal_id: int, datos: PublicacionEntrada,
                           coordinador: Usuario = coordinacion):
        """#422: el coordinador corrige la publicación (y la ficha) de un animal disponible."""
        return _editar_publicacion(ctx, animal_id, datos, coordinador)

    @rutas.post("/refugio/animales/{animal_id}/publicacion/retiro")
    def retirar_publicacion(animal_id: int, coordinador: Usuario = coordinacion):
        """#450: el coordinador retira de la adopción (sin borrar) un animal publicado."""
        return _retirar_publicacion(ctx, animal_id, coordinador)

    @rutas.get("/adopciones/animales")
    def catalogo_de_adopcion():
        """Público: animales disponibles. Sin datos del refugio ni de personas (RN-14)."""
        con_foto = repositorio_fotos.con_foto()
        return [_publicacion(p, con_foto) for p in ctx.repositorio_adopciones.disponibles()]

    @rutas.get("/adopciones/animales/{animal_id}/foto")
    def foto_del_animal(animal_id: int):
        """Pública, como el catálogo. Se envía con el tipo verificado y nosniff: el navegador
        no intenta adivinar otro tipo (no se puede colar un HTML como imagen)."""
        foto = _exigir(repositorio_fotos.foto(animal_id), "Este animal no tiene foto.")
        return Response(foto[1], media_type=foto[0], headers={
            "X-Content-Type-Options": "nosniff", "Cache-Control": "public, max-age=3600"})

    @rutas.post("/refugio/animales/{animal_id}/foto", status_code=201)
    async def subir_foto(animal_id: int, foto: Annotated[UploadFile, File()],
                         coordinador: Usuario = coordinacion):
        """RF-25: foto del animal de su refugio (JPEG, PNG o WebP de hasta 300 KB)."""
        return await _subir_foto(ctx, animal_id, foto, coordinador)

    @rutas.get("/adopciones/recomendaciones")
    def recomendaciones(adoptante: Usuario = adoptante_actual):
        """RF-09: animales disponibles ordenados por compatibilidad con SU hogar, con puntaje
        y 3 razones. Los que tienen una restricción dura (RN-05) no aparecen."""
        return _recomendaciones(ctx, adoptante)


def _rutas_de_solicitudes(rutas: APIRouter, ctx: Contexto) -> None:
    """Solicitudes de adopción: pedir, listar, proponer la jornada y decidir (RF-27, RF-28)."""
    adoptante_actual, coordinacion, adopciones = (ctx.adoptante_actual, ctx.coordinacion,
                                                  ctx.adopciones)

    @rutas.post("/adopciones/solicitudes", status_code=201)
    def solicitar_adopcion(datos: SolicitudEntrada, adoptante: Usuario = adoptante_actual):
        """RF-27, RN-10: perfil lleno y seguimiento aceptado; una pendiente por animal."""
        s = _traducir(ERRORES_SOLICITAR, adopciones.solicitar, adoptante, datos.animal_id,
                      datos.mensaje)
        return {"id": s.id, "animal_id": s.animal_id, "estado": s.estado.value}

    @rutas.get("/adopciones/solicitudes/mias")
    def mis_solicitudes(adoptante: Usuario = adoptante_actual):
        return _mis_solicitudes(ctx, adoptante)

    @rutas.get("/refugio/solicitudes")
    def solicitudes_del_refugio(coordinador: Usuario = coordinacion):
        """Las solicitudes por animales de SU refugio, con el perfil del adoptante: es lo que
        el coordinador necesita para decidir (y nada más: ni contraseña ni otros datos)."""
        return _solicitudes_del_refugio(ctx, coordinador)

    @rutas.get("/refugio/jornada/propuesta")
    def propuesta_de_jornada(coordinador: Usuario = coordinacion):
        """RF-28: con los adoptantes que tienen solicitudes pendientes en su refugio y los
        animales disponibles de su refugio, la combinación que maximiza la compatibilidad
        total. Es una propuesta: no aprueba nada (RN-16)."""
        return _propuesta_de_jornada(ctx, coordinador)

    @rutas.post("/refugio/solicitudes/{solicitud_id}/decision")
    def decidir_solicitud(solicitud_id: int, datos: DecisionEntrada, peticion: Request,
                          coordinador: Usuario = coordinacion):
        """RF-27: aprobar (RN-05, RN-11; egreso por adopción y seguimientos RF-10) o
        rechazar con razón. Solo solicitudes de animales de su refugio."""
        return _decidir_solicitud(ctx, solicitud_id, datos, peticion, coordinador)

    @rutas.post("/refugio/solicitudes/{solicitud_id}/visita")
    def pedir_visita(solicitud_id: int, datos: NotaSolicitudEntrada,
                     coordinador: Usuario = coordinacion):
        """RF-27: pedir una visita previa antes de aprobar o rechazar."""
        return _anotar_solicitud(ctx, adopciones.pedir_visita, ERRORES_VISITA, "nota",
                                 solicitud_id, datos.texto, coordinador)

    @rutas.post("/refugio/solicitudes/{solicitud_id}/devolucion")
    def registrar_devolucion(solicitud_id: int, datos: NotaSolicitudEntrada,
                             coordinador: Usuario = coordinacion):
        """RF-10, RN-13: devolución con su motivo; el animal reingresa y vuelve al catálogo."""
        return _anotar_solicitud(ctx, adopciones.devolver, ERRORES_DEVOLUCION, "motivo",
                                 solicitud_id, datos.texto, coordinador)


def _rutas_de_seguimientos(rutas: APIRouter, ctx: Contexto) -> None:
    """Seguimientos después de adoptar (RF-10) y compromiso en PDF (RF-29)."""
    coordinacion = ctx.coordinacion
    acceso_adopcion = exigir_rol(ctx.dependencia_usuario, Rol.ADOPTANTE, Rol.COORDINADOR)

    @rutas.get("/refugio/seguimientos")
    def seguimientos_del_refugio(coordinador: Usuario = coordinacion):
        """RF-10: seguimientos de las adopciones de animales de su refugio, los pendientes
        primero y por fecha."""
        return _seguimientos_del_refugio(ctx, coordinador)

    @rutas.post("/refugio/seguimientos/{seguimiento_id}")
    def registrar_seguimiento(seguimiento_id: int, datos: SeguimientoEntrada,
                              coordinador: Usuario = coordinacion):
        return _registrar_seguimiento(ctx, seguimiento_id, datos, coordinador)

    @rutas.get("/adopciones/solicitudes/{solicitud_id}/compromiso.pdf")
    def compromiso_de_adopcion(solicitud_id: int, usuario: Usuario = acceso_adopcion):
        """RF-29: el adoptante de la solicitud o el coordinador del refugio del animal; para
        cualquier otro la solicitud «no existe» (404), así no se adivinan solicitudes ajenas."""
        return _compromiso_de_adopcion(ctx, solicitud_id, usuario)
