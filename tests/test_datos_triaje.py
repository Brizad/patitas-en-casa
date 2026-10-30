"""Datos sintéticos v2 del triaje (fase 7): tamaño, semilla, conjuntos y casos difíciles."""
import random
from collections import Counter
from pathlib import Path

import pytest

from scripts.ia.datos_triaje import (
    NEGACIONES_PRUEBA,
    ORDEN,
    SOLO_PRUEBA,
    conjuntos,
    ensuciar,
    generar,
    leer,
)

PRUEBA_FIJA = Path(__file__).resolve().parents[1] / "scripts" / "ia" / "datos" / "triaje_prueba.csv"


@pytest.fixture(scope="module")
def datos():
    return conjuntos()


def test_hay_mas_de_cinco_mil_reportes_en_total(datos):
    assert sum(len(filas) for filas in datos.values()) >= 5000


def test_la_misma_semilla_da_los_mismos_datos():
    assert generar(200, semilla=9) == generar(200, semilla=9)
    assert generar(200, semilla=9) != generar(200, semilla=10)


def test_entrenamiento_balanceado_y_con_las_cuatro_prioridades(datos):
    cuenta = Counter(e for _, e, _ in datos["entrenamiento"])
    assert set(cuenta) == set(ORDEN) and len(set(cuenta.values())) == 1


def test_ningun_texto_de_prueba_aparece_al_entrenar_o_validar(datos):
    vistos = {t for nombre in ("entrenamiento", "validacion") for t, _, _ in datos[nombre]}
    assert not vistos & {t for t, _, _ in datos["prueba"]}


def test_todos_cumplen_rn01_veinte_caracteres(datos):
    assert all(len(t) >= 20 for filas in datos.values() for t, _, _ in filas)


def test_la_prueba_tiene_mitad_de_casos_dificiles(datos):
    casos = Counter(c for _, _, c in datos["prueba"])
    assert casos["comun"] == 600
    assert casos["frase_nueva"] == casos["negacion"] == casos["ruido_fuerte"] == 200


def test_las_frases_reservadas_nunca_se_usan_al_entrenar(datos):
    reservadas = [f for d in (SOLO_PRUEBA, NEGACIONES_PRUEBA) for fs in d.values() for f in fs]
    textos = " ".join(t.lower() for t, _, _ in datos["entrenamiento"])
    assert not [f for f in reservadas if f in textos]


def test_el_ruido_cambia_el_texto_pero_no_lo_vacia():
    rng = random.Random(1)
    original = "Por favor vengan, un perro está muy flaco porque no come hace días."
    sucios = {ensuciar(rng, original, 0.9) for _ in range(20)}
    assert original not in sucios and all(len(s) > 20 for s in sucios)


def test_el_archivo_de_prueba_fijo_es_el_que_genera_el_programa(datos):
    assert leer(PRUEBA_FIJA) == datos["prueba"]  # si cambia el generador, esto avisa
