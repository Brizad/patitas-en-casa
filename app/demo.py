"""Datos de demostración para mostrar el sistema (#109).

Render (plan gratis) no tiene consola, así que los datos se cargan solos al arrancar si
PATITAS_DEMO_ACTIVA=true y PATITAS_DEMO_CONTRASENA existen. La contraseña de las cuentas de
demostración NUNCA está en el código: la escribe Brayan en Render.

Todo es ficticio: correos del dominio inventado demo.patitas.co, reportes y animales
inventados. La carga es idempotente: si la cuenta del veterinario de demostración ya existe,
no hace nada (cada reinicio de Render vuelve a ejecutar el arranque).

Qué deja listo para el guion de la demostración (docs/aprende/guion-demo.md):
- Una cuenta por rol: administrador, veterinario, coordinador, rescatista, adoptante y Alcaldía.
- Reportes en varias comunas de Cúcuta: unos en la cola, uno crítico confirmado esperando
  rescatista (oferta) y uno ya rescatado.
- Animales en el refugio con historial clínico, y tres publicados para adopción.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.adopciones.modelos import Energia, PerfilAdoptante, Publicacion, Tamano, Vivienda
from app.adopciones.repositorio import RepositorioAdopciones
from app.cupos.fichas import ServicioFichas
from app.cupos.repositorio import RepositorioCupos
from app.cupos.servicio import ServicioCupos
from app.dominio.modelos import (
    Animal,
    Especie,
    Prioridad,
    ResultadoRescate,
    Rol,
    TipoNota,
    Ubicacion,
)
from app.reportes.confirmacion import ServicioConfirmacion
from app.reportes.servicio import ServicioReportes
from app.rescates.servicio import ServicioRescates
from app.usuarios.repositorio import RepositorioUsuarios
from app.usuarios.servicio import ServicioUsuarios

logger = logging.getLogger(__name__)

DOMINIO = "demo.patitas.co"
CUENTAS = [  # (usuario, nombre, rol)
    ("admin", "Administración (demo)", Rol.ADMINISTRADOR),
    ("veterinaria", "Dra. Ana Pérez (demo)", Rol.VETERINARIO),
    ("coordinador", "Carlos Rincón (demo)", Rol.COORDINADOR),
    ("rescatista", "Rita Gómez (demo)", Rol.RESCATISTA),
    ("adoptante", "Laura Duarte (demo)", Rol.ADOPTANTE),
    ("alcaldia", "Secretaría de Salud (demo)", Rol.ALCALDIA),
]
# (descripción, latitud, longitud, comuna). Coordenadas aproximadas de Cúcuta.
REPORTES = [
    ("Perro atropellado en la avenida Libertadores, no se mueve y sangra mucho",
     7.8890, -72.4966, 2),
    ("Gata con una herida abierta en el lomo, está escondida debajo de un carro",
     7.8762, -72.5101, 6),
    ("Perrito que cojea un poco y no come hace dos días frente a la tienda",
     7.9073, -72.5053, 7),
    ("Perra con sarna y garrapatas que duerme en el parque del barrio",
     7.8679, -72.5235, 8),
    ("Gato convulsionando en la acera, parece que lo envenenaron",
     7.8995, -72.4870, 3),
    ("Cachorro abandonado en una caja frente al colegio, se ve sano pero asustado",
     7.8833, -72.5160, 5),
    ("Perro con una fractura en la pata trasera, no se puede parar",
     7.8930, -72.5072, 1),
]
ANIMALES = [  # (nombre, especie, estado de salud, publicación o None)
    ("Canela", Especie.GATO, "Desnutrición leve, en recuperación",
     ("Gata tranquila y cariñosa, le encanta dormir al sol", Tamano.PEQUENO, Energia.BAJA,
      24, True, False, False)),
    ("Toby", Especie.PERRO, "Sano, vacunado y esterilizado",
     ("Perro juguetón que ama correr y convive bien con niños", Tamano.GRANDE, Energia.ALTA,
      18, True, True, True)),
    ("Luna", Especie.PERRO, "Recuperada de una fractura en la pata",
     ("Perrita mediana, dulce y tranquila, ideal para apartamento", Tamano.MEDIANO,
      Energia.MEDIA, 36, True, True, False)),
    ("Michi", Especie.GATO, "En tratamiento por sarna", None),
]


@dataclass
class Dependencias:
    usuarios: RepositorioUsuarios
    reportes: ServicioReportes
    confirmaciones: ServicioConfirmacion
    rescates: ServicioRescates
    cupos: RepositorioCupos
    adopciones: RepositorioAdopciones


def correo(usuario: str) -> str:
    return f"{usuario}@{DOMINIO}"


def cargar_demo(d: Dependencias, contrasena: str) -> bool:
    """Carga los datos si aún no existen. True si los cargó."""
    if d.usuarios.buscar_por_correo(correo("veterinaria")) is not None:
        return False
    servicio = ServicioUsuarios(d.usuarios)
    cuentas = {u: servicio.registrar(correo(u), nombre, rol, contrasena)
               for u, nombre, rol in CUENTAS}
    # El veterinario trabaja en el mismo refugio: ve sus fichas (manual de usuario, #156).
    for usuario in ("coordinador", "veterinaria"):
        d.usuarios.vincular_refugio(correo(usuario), 1)
    vet, resc = cuentas["veterinaria"], cuentas["rescatista"]
    d.rescates.cambiar_disponibilidad(resc, True)  # zona vacía = toda la ciudad

    codigos = [d.reportes.registrar(texto, Ubicacion(lat, lon, None, comuna)).codigo
               for texto, lat, lon, comuna in REPORTES]
    # El primero (atropellado): confirmado, aceptado y trasladado al refugio.
    d.confirmaciones.confirmar(codigos[0], vet)
    d.rescates.aceptar(resc, codigos[0])
    d.rescates.llegue(resc, codigos[0])
    d.rescates.registrar_resultado(resc, codigos[0], ResultadoRescate.TRASLADADO)
    # El quinto (convulsión): confirmado crítico y esperando rescatista (oferta abierta).
    d.confirmaciones.confirmar(codigos[4], vet)
    # El cuarto (sarna): el veterinario lo ajusta a baja con justificación.
    d.confirmaciones.confirmar(codigos[3], vet, Prioridad.BAJA,
                               "Solo sarna y garrapatas, sin heridas visibles")
    # Los demás quedan en la cola para mostrar la confirmación en vivo.

    cupos, fichas = ServicioCupos(d.cupos, _SinAvisos()), ServicioFichas(d.cupos)
    for nombre, especie, salud, publicacion in ANIMALES:
        animal = Animal(nombre, especie, salud, vacunado=True, esterilizado=nombre != "Michi")
        cupos.registrar_ingreso(animal)
        fichas.agregar_nota(animal.id, vet, TipoNota.OBSERVACION,
                            f"Ingreso de {nombre}: {salud.lower()}")
        if publicacion:
            d.adopciones.publicar(Publicacion(animal.id, *publicacion, nombre=nombre,
                                              especie=especie.value))
    d.adopciones.guardar_perfil(PerfilAdoptante(
        correo("adoptante"), Vivienda.APARTAMENTO, tiene_patio=False, hay_ninos=True,
        otros_animales=False, horas_solo_al_dia=5, experiencia=True, acepta_seguimiento=True))
    logger.info("Datos de demostración cargados (%d cuentas, %d reportes, %d animales).",
                len(CUENTAS), len(REPORTES), len(ANIMALES))
    return True


class _SinAvisos:
    """Los ingresos de demostración no deben mandar alertas de cupo por correo."""

    def enviar(self, destinatario: str, mensaje: str) -> None:
        pass
