"""#508: perfil de adopción del animal (estadísticas 1 a 5, tipo, habilidades y salud).

Todo sale de la ficha real: si un dato falta, no se inventa (ni barra, ni tipo, ni insignia).
"""
from dataclasses import replace

import pytest

from app.adopciones.modelos import Energia, Publicacion, Tamano
from app.adopciones.perfil import HABILIDADES, estadisticas, nivel, perfil_de_adopcion, tipo
from app.dominio.modelos import Animal, Especie
from tests.test_publicacion import DATOS, FICHA, c, ingresar, repos, sesion  # noqa: F401


def _publicacion(**cambios) -> Publicacion:
    datos = {"animal_id": 1, "descripcion": "Perrita tranquila y muy cariñosa",
             "tamano": Tamano.PEQUENO,
             "energia": Energia.BAJA, "edad_meses": 24, "apto_ninos": True,
             "apto_otros_animales": True, "necesita_patio": False, "nombre": "Lupe",
             "especie": "perro"}
    return Publicacion(**(datos | cambios))


@pytest.mark.parametrize(("valor", "esperado"), [
    (None, None), (0, 1), (1, 1), (20, 1), (21, 2), (40, 2), (41, 3), (60, 3), (61, 4),
    (80, 4), (81, 5), (100, 5)])
def test_nivel_de_0_a_100_a_1_a_5(valor, esperado):
    assert nivel(valor) == esperado


def test_las_estadisticas_salen_de_los_niveles_de_la_ficha():
    p = _publicacion(energia_nivel=45, carino=94, juego=55, calma=95)
    assert estadisticas(p) == {"energia": 3, "carino": 5, "juego": 3, "paciencia": 5}


def _est(energia, carino, juego, paciencia):
    return {"energia": energia, "carino": carino, "juego": juego, "paciencia": paciencia}


@pytest.mark.parametrize(("est", "esperado"), [
    (_est(3, 3, 4, 3), "jugueton"),      # Juego alto
    (_est(5, 5, 5, 1), "jugueton"),      # Juego alto va primero
    (_est(4, 3, 3, 3), "aventurero"),    # Energía alta
    (_est(2, 3, 3, 4), "tranquilo"),     # Energía baja y Paciencia alta
    (_est(1, 5, 2, 5), "tranquilo"),     # Tranquilo va antes que Cariñoso
    (_est(3, 4, 3, 3), "carinoso"),      # Cariño alto
    (_est(3, 3, 3, 4), "guardian"),      # Paciencia alta y Energía media
    (_est(3, 3, 3, 3), None),            # ninguna regla: sin tipo
    (_est(2, 3, 3, 3), None),            # Energía baja sin Paciencia alta
])
def test_el_tipo_se_calcula_con_la_regla_fija(est, esperado):
    assert tipo(est) == esperado


def test_sin_estadisticas_completas_no_hay_tipo():
    assert tipo(_est(None, None, None, None)) is None
    assert tipo(_est(3, 3, 3, None)) is None  # Guardián necesitaría la paciencia: no se supone


def test_sin_datos_no_se_dibuja_nada():
    perfil = perfil_de_adopcion(_publicacion())
    assert perfil == {"estadisticas": {"energia": None, "carino": None, "juego": None,
                                       "paciencia": None},
                      "tipo": None, "habilidades": [],
                      "salud": {"vacunas": None, "esterilizado": None, "desparasitado": None}}


def test_perfil_completo_con_habilidades_y_salud_de_la_ficha():
    p = _publicacion(energia_nivel=95, carino=70, juego=40, calma=50,
                     habilidades=["Ama caminar"], vacunas=True, esterilizado=False)
    perfil = perfil_de_adopcion(p)
    assert perfil["tipo"] == "aventurero"
    assert perfil["habilidades"] == ["Ama caminar"]
    assert perfil["salud"] == {"vacunas": True, "esterilizado": False, "desparasitado": None}


def test_catalogo_fijo_de_habilidades():
    assert HABILIDADES == ("Bueno con niños", "Le gustan otros perros", "Le gustan los gatos",
                           "Ideal apartamento", "Experto en siestas", "Ama caminar",
                           "Rey del juego", "Abuelito tierno")


# ---------- en la API y en los dos repositorios ----------


def test_el_catalogo_trae_el_perfil_calculado_y_sin_datos_nada(c):  # noqa: F811
    h = sesion(c)
    c.post(f"/refugio/animales/{ingresar(c, h)}/publicacion", json={**DATOS, **FICHA}, headers=h)
    c.post(f"/refugio/animales/{ingresar(c, h, 'Nube')}/publicacion", json=DATOS, headers=h)
    toby, nube = c.get("/adopciones/animales").json()
    # FICHA: energía 92, cariño 95, juego 90 y calma 38 → 5, 5, 5 y 2: Juguetón.
    assert toby["estadisticas"] == {"energia": 5, "carino": 5, "juego": 5, "paciencia": 2}
    assert toby["tipo"] == "jugueton"
    assert nube["estadisticas"] == dict.fromkeys(("energia", "carino", "juego", "paciencia"))
    assert (nube["tipo"], nube["habilidades"]) == (None, [])
    assert nube["salud"] == {"vacunas": None, "esterilizado": None, "desparasitado": None}


def test_habilidades_y_salud_se_guardan_y_se_leen(repos):  # noqa: F811
    cupos, adopciones = repos
    lupe = Animal("Lupe", Especie.PERRO, "sana")
    cupos.ocupar_cupo(lupe)
    adopciones.publicar(Publicacion(lupe.id, "Perrita dormilona y muy cariñosa", Tamano.PEQUENO,
                                    Energia.BAJA, 60, True, True, False, nombre="Lupe",
                                    especie="perro"))
    assert adopciones.publicacion(lupe.id).habilidades == []
    nueva = replace(adopciones.publicacion(lupe.id), habilidades=["Experto en siestas"],
                    vacunas=True, esterilizado=False)
    assert adopciones.actualizar_publicacion(nueva) is True
    leida = adopciones.publicacion(lupe.id)
    assert leida.habilidades == ["Experto en siestas"]
    assert (leida.vacunas, leida.esterilizado, leida.desparasitado) == (True, False, None)
