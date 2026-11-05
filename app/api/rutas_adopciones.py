"""Rutas de adopción: adoptante, catálogo, fotos, recomendaciones y gestión del refugio (RF-08 a
RF-10, RF-25 a RF-29) (DT-13, #267)."""
from __future__ import annotations

import logging
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
from pydantic import BaseModel, Field
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


# C901: como en crear_app, mccabe suma las rutas anidadas; cada una es sencilla.
def crear_rutas_adopciones(ctx: Contexto) -> APIRouter:  # noqa: C901
    rutas = APIRouter()
    ip_de = ctx.ip_de  # A-04 (#278)
    dependencia_usuario = ctx.dependencia_usuario
    repositorio_refugios = ctx.repositorio_refugios
    repositorio_usuarios = ctx.repositorio_usuarios
    adopciones = ctx.adopciones
    adoptante_actual = ctx.adoptante_actual
    coordinacion = ctx.coordinacion
    fichas_de = ctx.fichas_de
    limite_intentos = ctx.limite_intentos
    repositorio_adopciones = ctx.repositorio_adopciones
    repositorio_fotos = ctx.repositorio_fotos
    usuarios = ctx.usuarios
    notificador = ctx.notificador

    def avisar_registro_duplicado(correo: str) -> None:
        """P-12: corre después de responder (BackgroundTasks). Una falla queda en el log."""
        try:
            notificador.enviar(correo, AVISO_REGISTRO_DUPLICADO)
        except Exception:
            logger.exception("No se pudo avisar al dueño de un correo ya registrado.")

    # --- Fase 3 (#85): adoptante (RF-08) ---------------------------------------------

    @rutas.post("/adoptantes", status_code=201)
    def registrar_adoptante(datos: RegistroAdoptante, peticion: Request,
                            tareas: BackgroundTasks):
        """Público, como el reporte: el adoptante no es personal y crea su propia cuenta.
        El rol siempre es adoptante; nadie puede registrarse como personal por aquí.

        DT-09 (#149): máximo REGISTROS_MAXIMOS_POR_IP intentos por IP en la ventana (429), y
        la misma respuesta exista o no el correo: así nadie averigua quién tiene cuenta."""
        clave = clave_registro(ip_de(peticion))
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
            if config.AVISAR_REGISTRO_DUPLICADO:  # P-12: apagado por defecto
                tareas.add_task(avisar_registro_duplicado, normalizar_correo(datos.correo))
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

    @rutas.get("/refugio/solicitudes")
    def solicitudes_del_refugio(coordinador: Usuario = coordinacion):
        """Las solicitudes por animales de SU refugio, con el perfil del adoptante: es lo que
        el coordinador necesita para decidir (y nada más: ni contraseña ni otros datos)."""
        animales = fichas_de(coordinador)
        respuesta = []
        for s in repositorio_adopciones.solicitudes():
            animal = animales.animal(s.animal_id)
            if animal is None:
                continue
            perfil = repositorio_adopciones.perfil(s.adoptante)
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
                    calcular(perfil, repositorio_adopciones.publicacion(s.animal_id)))})
        return respuesta

    @rutas.get("/refugio/jornada/propuesta")
    def propuesta_de_jornada(coordinador: Usuario = coordinacion):
        """RF-28: con los adoptantes que tienen solicitudes pendientes en su refugio y los
        animales disponibles de su refugio, la combinación que maximiza la compatibilidad
        total. Es una propuesta: no aprueba nada (RN-16)."""
        animales = fichas_de(coordinador)
        disponibles = [a for a in repositorio_adopciones.disponibles()
                       if animales.animal(a.animal_id) is not None]
        pendientes = [s for s in repositorio_adopciones.solicitudes()
                      if s.estado == EstadoSolicitud.PENDIENTE
                      and animales.animal(s.animal_id) is not None]
        adoptantes = list(dict.fromkeys(s.adoptante for s in pendientes))
        perfiles = [repositorio_adopciones.perfil(c) for c in adoptantes]
        if not disponibles or not adoptantes:
            return []
        tabla = [[calcular(p, a) for a in disponibles] for p in perfiles]
        pidio = {(s.adoptante, s.animal_id) for s in pendientes}
        return [{"adoptante": adoptantes[i], "animal_id": disponibles[j].animal_id,
                 "animal": disponibles[j].nombre, **_compatibilidad(tabla[i][j]),
                 "solicito_este_animal": (adoptantes[i], disponibles[j].animal_id) in pidio}
                for i, j in asignar([[c.puntaje for c in fila] for fila in tabla])]

    @rutas.post("/refugio/solicitudes/{solicitud_id}/decision")
    def decidir_solicitud(solicitud_id: int, datos: DecisionEntrada, peticion: Request,
                          coordinador: Usuario = coordinacion):
        """RF-27: aprobar (RN-05, RN-11; egreso por adopción y seguimientos RF-10) o
        rechazar con razón. Solo solicitudes de animales de su refugio."""
        solicitud = repositorio_adopciones.solicitud(solicitud_id)
        if solicitud is None or fichas_de(coordinador).animal(solicitud.animal_id) is None:
            raise HTTPException(status_code=404, detail="No hay esa solicitud en tu refugio.")
        try:
            s = adopciones.decidir(coordinador, solicitud_id, datos.aprobar, datos.razon)
            _cambio(peticion, {"estado": solicitud.estado.value}, {"estado": s.estado.value})
        except SolicitudNoEncontrada as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (SolicitudYaDecidida, RestriccionDura) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RazonInvalida as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": s.id, "estado": s.estado.value, "razon": s.razon,
                "seguimientos": [{"dia": x.dia, "programado_para": fecha_utc(x.programado_para)}
                                 for x in repositorio_adopciones.seguimientos(solicitud_id)]}

    def _solicitud_del_refugio(solicitud_id: int, coordinador: Usuario) -> None:
        s = repositorio_adopciones.solicitud(solicitud_id)
        if s is None or fichas_de(coordinador).animal(s.animal_id) is None:
            raise HTTPException(status_code=404, detail="No hay esa solicitud en tu refugio.")

    @rutas.post("/refugio/solicitudes/{solicitud_id}/visita")
    def pedir_visita(solicitud_id: int, datos: NotaSolicitudEntrada,
                     coordinador: Usuario = coordinacion):
        """RF-27: pedir una visita previa antes de aprobar o rechazar."""
        _solicitud_del_refugio(solicitud_id, coordinador)
        try:
            s = adopciones.pedir_visita(coordinador, solicitud_id, datos.texto)
        except SolicitudYaDecidida as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RazonInvalida as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": s.id, "estado": s.estado.value, "nota": s.razon}

    @rutas.post("/refugio/solicitudes/{solicitud_id}/devolucion")
    def registrar_devolucion(solicitud_id: int, datos: NotaSolicitudEntrada,
                             coordinador: Usuario = coordinacion):
        """RF-10, RN-13: devolución con su motivo; el animal reingresa y vuelve al catálogo."""
        _solicitud_del_refugio(solicitud_id, coordinador)
        try:
            s = adopciones.devolver(coordinador, solicitud_id, datos.texto)
        except (SolicitudYaDecidida, SinCupoParaDevolucion) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RazonInvalida as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": s.id, "estado": s.estado.value, "motivo": s.razon}

    @rutas.get("/refugio/seguimientos")
    def seguimientos_del_refugio(coordinador: Usuario = coordinacion):
        """RF-10: seguimientos de las adopciones de animales de su refugio, los pendientes
        primero y por fecha."""
        animales = fichas_de(coordinador)
        ahora = datetime.now(UTC)
        filas = []
        for s in repositorio_adopciones.solicitudes():
            animal = animales.animal(s.animal_id)
            if s.estado != EstadoSolicitud.APROBADA or animal is None:
                continue
            for x in repositorio_adopciones.seguimientos(s.id):
                filas.append({**_seguimiento(x, ahora), "solicitud_id": s.id,
                              "animal": animal.nombre, "adoptante": s.adoptante})
        return sorted(filas, key=lambda f: (f["realizado_en"] is not None,
                                            f["programado_para"]))

    @rutas.post("/refugio/seguimientos/{seguimiento_id}")
    def registrar_seguimiento(seguimiento_id: int, datos: SeguimientoEntrada,
                              coordinador: Usuario = coordinacion):
        mios = {f["id"] for f in seguimientos_del_refugio(coordinador)}
        if seguimiento_id not in mios:
            raise HTTPException(status_code=404, detail="No hay ese seguimiento en tu refugio.")
        try:
            hecho = adopciones.registrar_seguimiento(coordinador, seguimiento_id, datos.nota)
        except SeguimientoNoValido as error:
            raise HTTPException(status_code=409 if "registrado" in str(error) else 422,
                                detail=str(error)) from error
        return _seguimiento(hecho, datetime.now(UTC))

    acceso_adopcion = exigir_rol(dependencia_usuario, Rol.ADOPTANTE, Rol.COORDINADOR)

    @rutas.get("/adopciones/solicitudes/{solicitud_id}/compromiso.pdf")
    def compromiso_de_adopcion(solicitud_id: int, usuario: Usuario = acceso_adopcion):
        """RF-29: el adoptante de la solicitud o el coordinador del refugio del animal; para
        cualquier otro la solicitud «no existe» (404), así no se adivinan solicitudes ajenas."""
        s = repositorio_adopciones.solicitud(solicitud_id)
        if s is None or (s.adoptante != usuario.correo if usuario.rol == Rol.ADOPTANTE
                         else fichas_de(usuario).animal(s.animal_id) is None):
            raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
        if s.estado != EstadoSolicitud.APROBADA:
            raise HTTPException(status_code=409,
                                detail="El compromiso existe solo para adopciones aprobadas.")
        adoptante = repositorio_usuarios.buscar_por_correo(s.adoptante)
        pdf = generar_pdf(lineas_compromiso(
            s, repositorio_adopciones.publicacion(s.animal_id),
            adoptante.nombre if adoptante else s.adoptante,
            repositorio_adopciones.seguimientos(s.id),
            repositorio_refugios.de_animal(s.animal_id)))
        return Response(pdf, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="compromiso-{s.id}.pdf"'})

    return rutas
