"""Perfil de adopción del animal (#508): estadísticas, tipo, habilidades y salud.

Solo para mostrar en «Adoptar»: la compatibilidad (RF-09) no cambia. Todo sale de la ficha real:
si un dato falta, aquí queda None (o lista vacía) y la página no dibuja esa barra, ese tipo ni
esa insignia. Nunca hay valores por defecto.

Estadísticas de 1 a 5. Se derivan de los niveles 0-100 que la publicación ya tenía (#422):
    Energía = energia_nivel · Cariño = carino · Juego = juego · Paciencia = calma
    nivel = techo(valor / 20), entre 1 y 5 (0-20 → 1, 21-40 → 2, 41-60 → 3, 61-80 → 4, 81-100 → 5)

Tipo: se CALCULA, nunca se escribe a mano. Solo con las 4 estadísticas. «Alto» es 4 o 5,
«medio» es 3 y «bajo» es 1 o 2. Gana la primera regla que se cumple, en este orden:
    1. Juguetón   = Juego alto
    2. Aventurero = Energía alta
    3. Tranquilo  = Energía baja y Paciencia alta
    4. Cariñoso   = Cariño alto
    5. Guardián   = Paciencia alta y Energía media
Si ninguna se cumple, no hay tipo. La misma regla está en docs/adopcion/perfil-de-adopcion.md.
"""
from __future__ import annotations

from math import ceil

from app.adopciones.modelos import Publicacion

# De qué nivel 0-100 de la publicación sale cada estadística.
ORIGEN = {"energia": "energia_nivel", "carino": "carino", "juego": "juego", "paciencia": "calma"}

# Catálogo fijo: el personal elige de aquí, no escribe texto libre.
HABILIDADES = ("Bueno con niños", "Le gustan otros perros", "Le gustan los gatos",
               "Ideal apartamento", "Experto en siestas", "Ama caminar", "Rey del juego",
               "Abuelito tierno")

SALUD = ("vacunas", "esterilizado", "desparasitado")  # sí (True), no (False) o sin dato (None)

TIPOS = ("jugueton", "aventurero", "tranquilo", "carinoso", "guardian")


def nivel(valor: int | None) -> int | None:
    """Nivel 0-100 de la ficha → estadística 1-5 (None si no hay dato)."""
    return None if valor is None else min(5, max(1, ceil(valor / 20)))


def a_cien(estadistica: int | None) -> int | None:
    """Estadística 1-5 → nivel 0-100 que se guarda (20, 40, 60, 80 o 100)."""
    return None if estadistica is None else estadistica * 20


def estadisticas(p: Publicacion) -> dict[str, int | None]:
    return {clave: nivel(getattr(p, campo)) for clave, campo in ORIGEN.items()}


def tipo(est: dict[str, int | None]) -> str | None:
    """La regla fija del encabezado. None si falta alguna estadística o ninguna regla aplica."""
    if any(v is None for v in est.values()):
        return None
    alto = {k: v >= 4 for k, v in est.items()}
    bajo = {k: v <= 2 for k, v in est.items()}
    medio = {k: v == 3 for k, v in est.items()}
    reglas = (("jugueton", alto["juego"]),
              ("aventurero", alto["energia"]),
              ("tranquilo", bajo["energia"] and alto["paciencia"]),
              ("carinoso", alto["carino"]),
              ("guardian", alto["paciencia"] and medio["energia"]))
    return next((nombre for nombre, cumple in reglas if cumple), None)


def perfil_de_adopcion(p: Publicacion) -> dict:
    est = estadisticas(p)
    return {"estadisticas": est, "tipo": tipo(est), "habilidades": list(p.habilidades),
            "salud": {campo: getattr(p, campo) for campo in SALUD}}
