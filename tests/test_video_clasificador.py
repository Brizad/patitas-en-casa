"""Clasificador de la marcha (#125, RF-03, RNF-09): MLP + reglas de seguridad."""
import pytest
from patitas_video import marcha
from patitas_video.clasificador import ClasificadorMarcha, Resultado

from tests.trayectorias_video import FPS, caminar


@pytest.fixture(scope="module")
def clasificador():
    return ClasificadorMarcha.desde_json()


def medir(cuadros):
    return marcha.medir(cuadros, FPS)


def test_el_clasificador_da_baja_a_la_marcha_normal_con_tres_evidencias(clasificador):
    r = clasificador.clasificar(medir(caminar()))
    assert isinstance(r, Resultado)
    assert r.prioridad == "baja"
    assert len(r.evidencias) >= 3  # RNF-09
    assert any("de pie" in e for e in r.evidencias)


def test_la_cojera_sube_a_media_o_mas(clasificador):
    r = clasificador.clasificar(medir(caminar(amplitud={"back_left_paw": 5.0})))
    assert r.prioridad in ("media", "alta", "critica")
    assert any("cojea" in e for e in r.evidencias)


@pytest.mark.parametrize("cuadros", [caminar(levantada="back_left_paw"), caminar(echado=True)])
def test_regla_de_seguridad_sin_apoyo_o_sin_ponerse_de_pie_nunca_bajo_alta(clasificador,
                                                                           cuadros):
    r = clasificador.clasificar(medir(cuadros))
    assert r.prioridad in ("alta", "critica")


def test_la_regla_de_seguridad_manda_aunque_el_modelo_diga_baja():
    """Aunque el modelo se equivoque (aquí siempre dice «baja»), la regla sube a alta."""
    tonto = ClasificadorMarcha.desde_json()
    tonto.probabilidades = lambda _x: {"critica": 0.0, "alta": 0.0, "media": 0.0, "baja": 1.0}
    r = tonto.clasificar(medir(caminar(levantada="back_left_paw")))
    assert r.prioridad == "alta"
    assert any("regla de seguridad" in e for e in r.evidencias)


def test_un_perro_echado_y_quieto_es_critico(clasificador):
    assert clasificador.clasificar(medir(caminar(echado=True))).prioridad == "critica"


def test_el_modelo_dice_que_se_entreno_con_datos_sinteticos(clasificador):
    assert clasificador.version == "marcha-mlp-v1"
    assert "sintétic" in clasificador.origen_de_los_datos
