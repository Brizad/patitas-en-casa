"""Compatibilidad adoptante–animal con puntaje y razones (RF-09, RNF-16, fase 4, #95).

Es un modelo de puntaje transparente (no una caja negra): cinco factores con un máximo de
puntos cada uno, que suman 100. Así cada recomendación se explica con sus 3 factores más
fuertes (RF-09 pide puntaje y 3 factores) y el refugio puede discutir y cambiar los pesos.

RNF-16: solo se usan los atributos de ATRIBUTOS_USADOS, que describen el hogar y el animal.
Nunca edad, género, estrato, etnia, religión ni discapacidad de la persona; el perfil ni
siquiera los pide. Una prueba comprueba que el puntaje no cambia por nada más.

Las restricciones duras (RN-05) no se compensan con puntos: el animal no se recomienda.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.adopciones.modelos import Energia, PerfilAdoptante, Publicacion, Tamano, Vivienda
from app.adopciones.reglas import restricciones_duras

ATRIBUTOS_USADOS = {
    "perfil": ("vivienda", "tiene_patio", "hay_ninos", "otros_animales", "horas_solo_al_dia",
               "experiencia"),
    "animal": ("tamano", "energia", "edad_meses", "apto_ninos", "apto_otros_animales"),
}


@dataclass(frozen=True)
class Factor:
    puntos: int
    maximo: int
    razon: str


@dataclass(frozen=True)
class Compatibilidad:
    puntaje: int  # 0 a 100
    razones: list[str]  # los 3 factores con más puntos: por qué encaja
    alertas: list[str]  # factores con menos de la mitad de sus puntos: qué conversar
    restricciones: list[str]  # RN-05: si hay alguna, no se recomienda

    @property
    def recomendable(self) -> bool:
        return not self.restricciones


def _espacio(p: PerfilAdoptante, a: Publicacion) -> Factor:
    amplio = p.tiene_patio or p.vivienda == Vivienda.FINCA
    if a.tamano == Tamano.GRANDE:
        return (Factor(25, 25, "hogar con espacio para un animal grande") if amplio
                else Factor(8, 25, "animal grande para un espacio reducido"))
    if a.tamano == Tamano.MEDIANO:
        return Factor(25 if amplio else 18, 25, "el tamaño encaja con el espacio del hogar")
    return Factor(25, 25, "animal pequeño: se adapta a cualquier vivienda")


def _tiempo(p: PerfilAdoptante, a: Publicacion) -> Factor:
    tolera = {Energia.BAJA: 8, Energia.MEDIA: 6, Energia.ALTA: 4}[a.energia]
    exceso = max(0, p.horas_solo_al_dia - tolera)
    puntos = max(0, 25 - 6 * exceso)
    if exceso == 0:
        return Factor(puntos, 25, f"pasaría solo {p.horas_solo_al_dia} h, que tolera bien")
    return Factor(puntos, 25, f"pasaría solo {p.horas_solo_al_dia} h; con energía "
                              f"{a.energia.value} tolera unas {tolera} h")


def _experiencia(p: PerfilAdoptante, a: Publicacion) -> Factor:
    exigente = a.energia == Energia.ALTA or a.edad_meses < 12
    if not exigente:
        return Factor(20, 20, "no exige experiencia previa")
    return (Factor(20, 20, "tiene experiencia para un animal joven o muy activo")
            if p.experiencia else Factor(8, 20, "animal joven o muy activo y sin experiencia"))


def _convivencia(hay: bool, apto: bool, quien: str) -> Factor:
    if not hay:
        return Factor(15, 15, f"en el hogar no hay {quien}")
    return (Factor(15, 15, f"convive bien con {quien}") if apto
            else Factor(0, 15, f"no es apto para convivir con {quien}"))


def calcular(perfil: PerfilAdoptante, animal: Publicacion) -> Compatibilidad:
    factores = [_espacio(perfil, animal), _tiempo(perfil, animal),
                _experiencia(perfil, animal),
                _convivencia(perfil.hay_ninos, animal.apto_ninos, "niños"),
                _convivencia(perfil.otros_animales, animal.apto_otros_animales,
                             "otros animales")]
    restricciones = restricciones_duras(perfil, animal)
    puntaje = 0 if restricciones else sum(f.puntos for f in factores)
    # Las razones más fuertes primero: lo que más suma (en proporción a su máximo).
    razones = [f.razon for f in sorted(factores, key=lambda f: f.puntos / f.maximo,
                                       reverse=True)[:3]]
    alertas = [f.razon for f in factores if f.puntos < f.maximo / 2]
    return Compatibilidad(puntaje, razones, alertas, restricciones)


def recomendar(perfil: PerfilAdoptante,
               disponibles: list[Publicacion]) -> list[tuple[Publicacion, Compatibilidad]]:
    """RF-09: los animales recomendables, del más compatible al menos."""
    pares = [(a, calcular(perfil, a)) for a in disponibles]
    return sorted([(a, c) for a, c in pares if c.recomendable],
                  key=lambda par: par[1].puntaje, reverse=True)
