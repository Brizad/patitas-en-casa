"""Resultados del piloto de usabilidad (RNF-06, #197): tiempo de reporte y puntaje SUS."""
import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
RUTA = RAIZ / "scripts" / "operacion" / "resultados_piloto.py"
spec = importlib.util.spec_from_file_location("resultados_piloto", RUTA)
piloto = importlib.util.module_from_spec(spec)
sys.modules["resultados_piloto"] = piloto
spec.loader.exec_module(piloto)

ENCABEZADO = "participante,segundos," + ",".join(f"sus_{i}" for i in range(1, 11))


def csv(*filas: str) -> str:
    return "\n".join([ENCABEZADO, *filas]) + "\n"


def test_sus_de_un_participante_ideal_es_100():
    # Ítems impares en 5 y pares en 1: lo mejor posible.
    assert piloto.puntaje_sus([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100


def test_sus_de_un_participante_pesimo_es_0():
    assert piloto.puntaje_sus([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0


def test_sus_neutral_es_50():
    assert piloto.puntaje_sus([3] * 10) == 50


def test_sus_exige_diez_respuestas_de_1_a_5():
    with pytest.raises(ValueError):
        piloto.puntaje_sus([3] * 9)
    with pytest.raises(ValueError):
        piloto.puntaje_sus([3] * 9 + [6])


def test_calcula_porcentaje_y_promedio():
    texto = csv(
        "P01,60,5,1,5,1,5,1,5,1,5,1",    # 100, cumple
        "P02,90,3,3,3,3,3,3,3,3,3,3",    # 50, cumple (90 es el límite)
        "P03,120,3,3,3,3,3,3,3,3,3,3",   # 50, no cumple
        "P04,45,5,1,5,1,5,1,5,1,5,1",    # 100, cumple
    )
    r = piloto.calcular(texto)
    assert r.participantes == 4
    assert r.cumplen_tiempo == 3
    assert r.porcentaje_tiempo == 75
    assert r.sus_promedio == 75
    assert r.cumple_tiempo is False   # 75 % < 80 %
    assert r.cumple_sus is True       # 75 >= 70


def test_las_filas_vacias_de_la_plantilla_se_ignoran():
    texto = csv("P01,60,5,1,5,1,5,1,5,1,5,1", "P02,,,,,,,,,,,", "P03,,,,,,,,,,,")
    assert piloto.calcular(texto).participantes == 1


def test_una_fila_a_medias_es_un_error_que_nombra_al_participante():
    with pytest.raises(ValueError, match="P02"):
        piloto.calcular(csv("P02,60,5,1,5"))


def test_sin_participantes_es_un_error():
    with pytest.raises(ValueError, match="participantes"):
        piloto.calcular(csv("P01,,,,,,,,,,,"))


def test_la_plantilla_entregada_se_lee_sin_error_y_esta_vacia():
    plantilla = (RAIZ / "docs" / "piloto" / "plantilla.csv").read_text(encoding="utf-8")
    assert plantilla.splitlines()[0] == ENCABEZADO
    with pytest.raises(ValueError, match="participantes"):
        piloto.calcular(plantilla)


def test_el_informe_dice_si_se_cumplen_las_metas():
    texto = csv("P01,60,5,1,5,1,5,1,5,1,5,1")
    informe = piloto.informe(piloto.calcular(texto))
    assert "100 %" in informe and "SUS" in informe and "CUMPLE" in informe
