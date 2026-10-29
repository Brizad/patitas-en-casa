"""Medidas de la marcha del video (#125, RF-03, RNF-09), sin video real.

El trabajador local calcula estas medidas con los puntos de DeepLabCut; aquí se prueban con
trayectorias sintéticas de un perro normal, cojo, con una pata sin apoyo y echado.
"""
import pytest
from patitas_video import marcha

from tests.trayectorias_video import FPS, caminar


def medir(cuadros):
    return marcha.medir(cuadros, FPS)


def test_un_perro_que_camina_normal_tiene_marcha_pareja():
    m = medir(caminar())
    assert m.cuadros_utiles == 1.0
    assert m.de_pie == 1.0
    assert m.asimetria < 0.1
    assert m.pata_sin_apoyo is None
    assert m.regularidad > 0.8
    assert m.desplazamiento == pytest.approx(1.0, abs=0.05)  # un largo de cuerpo por segundo


def test_la_cojera_aparece_como_asimetria_entre_patas_pareadas():
    m = medir(caminar(amplitud={"back_left_paw": 5.0}))
    assert m.asimetria > marcha.UMBRAL_COJERA
    assert m.pata_sin_apoyo is None


def test_una_pata_que_nunca_toca_el_suelo_se_detecta_por_su_nombre():
    m = medir(caminar(levantada="front_right_paw"))
    assert m.pata_sin_apoyo == "delantera derecha"
    assert m.fraccion_sin_apoyo == 1.0


def test_un_perro_echado_y_quieto_no_esta_de_pie_ni_se_desplaza():
    m = medir(caminar(echado=True))
    assert m.de_pie == 0.0
    assert m.desplazamiento < marcha.UMBRAL_INMOVIL


def test_sin_puntos_confiables_el_video_no_es_concluyente():
    cuadros = [{nombre: (x, y, 0.1) for nombre, (x, y, _c) in c.items()} for c in caminar()]
    m = medir(cuadros)
    assert m.cuadros_utiles == 0.0
    assert not m.concluyente
    assert not medir(caminar(segundos=1)).concluyente  # muy pocos cuadros
    assert not medir([]).concluyente


def test_si_el_medio_del_lomo_es_dudoso_se_usa_el_punto_medio_entre_cuello_y_cola():
    """Prueba de humo (#125): con videos reales, «back_middle» salió con confianza mediana de
    0,08 a 0,36. Sin él no se perdía solo ese punto sino el cuadro entero."""
    cuadros = [c | {"back_middle": (0.0, 0.0, 0.05)} for c in caminar()]
    m = medir(cuadros)
    assert m.cuadros_utiles == 1.0
    assert m.de_pie == 1.0  # el lomo sale de cuello y cola, a la misma altura


def test_umbral_de_confianza_calibrado_con_la_prueba_de_humo():
    """Los puntos de SuperAnimal en videos reales rondan 0,3 a 0,6: con 0,5 casi ningún cuadro
    servía. Un punto con 0,35 cuenta; uno con 0,2 no."""
    medio = [{k: (x, y, 0.35) for k, (x, y, _c) in c.items()} for c in caminar()]
    assert medir(medio).concluyente
    bajo = [{k: (x, y, 0.2) for k, (x, y, _c) in c.items()} for c in caminar()]
    assert not medir(bajo).concluyente
