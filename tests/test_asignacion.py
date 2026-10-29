"""RF-28 (#95): asignación global en jornadas (algoritmo húngaro) como propuesta."""
import itertools
import random

from app.adopciones.asignacion import asignar
from tests.test_decision_adopcion import PUBLICACION, en_memoria, h, preparar


def mejor_por_fuerza_bruta(puntajes):
    filas, columnas = len(puntajes), len(puntajes[0])
    mejor = 0
    for perm in itertools.permutations(range(max(filas, columnas)), filas):
        mejor = max(mejor, sum(puntajes[i][j] for i, j in enumerate(perm) if j < columnas))
    return mejor


def test_supera_al_voraz_en_el_caso_clasico():
    """El voraz da a Ana el animal 0 (90) y a Beto le queda el 1 (10): total 100.
    El óptimo da a Ana el 1 (80) y a Beto el 0 (85): total 165."""
    puntajes = [[90, 80], [85, 10]]
    parejas = asignar(puntajes)
    assert sorted(parejas) == [(0, 1), (1, 0)]
    assert sum(puntajes[i][j] for i, j in parejas) == 165


def test_coincide_con_la_fuerza_bruta_en_matrices_al_azar():
    rng = random.Random(3)
    for _ in range(40):
        filas, columnas = rng.randint(1, 5), rng.randint(1, 5)
        puntajes = [[rng.choice([0, rng.randint(1, 100)]) for _ in range(columnas)]
                    for _ in range(filas)]
        parejas = asignar(puntajes)
        assert len({j for _, j in parejas}) == len(parejas)  # un animal por persona
        assert sum(puntajes[i][j] for i, j in parejas) == mejor_por_fuerza_bruta(puntajes)


def test_no_propone_parejas_con_restriccion_dura():
    assert asignar([[0, 0], [0, 50]]) == [(1, 1)]
    assert asignar([]) == []


def test_api_propuesta_de_jornada():
    c = en_memoria()
    coord, _, _ = preparar(c)  # Canela no apta con niños: Lau (sin niños) sí, Ana no
    c.post("/refugio/ingresos", json={"nombre": "Toby", "especie": "perro",
                                      "estado_salud": "sano"}, headers=coord)
    toby = next(a["id"] for a in c.get("/refugio/animales", headers=coord).json()
                if a["nombre"] == "Toby")
    c.post(f"/refugio/animales/{toby}/publicacion",
           json={**PUBLICACION, "apto_ninos": True}, headers=coord)
    propuesta = c.get("/refugio/jornada/propuesta", headers=coord).json()
    parejas = {p["adoptante"]: p["animal"] for p in propuesta}
    assert parejas == {"lau@correo.co": "Canela", "ana@correo.co": "Toby"}
    assert all(len(p["razones"]) == 3 for p in propuesta)
    assert {p["adoptante"]: p["solicito_este_animal"] for p in propuesta} == {
        "lau@correo.co": True, "ana@correo.co": False}
    assert c.get("/refugio/jornada/propuesta",
                 headers=h(c, "lau@correo.co")).status_code == 403
