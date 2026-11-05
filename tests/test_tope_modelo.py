"""P-16 (#285): tope opcional de cuántos niveles sube el modelo sobre las reglas."""
from app import config
from app.dominio.modelos import Prioridad
from app.triaje.clasificador import Resultado
from app.triaje.combinado import combinar

REGLAS_MEDIA = Resultado(Prioridad.MEDIA, 0.4, [])
MODELO_CRITICA = Resultado(Prioridad.CRITICA, 0.99, ["«quieto» apunta a crítica"])


def test_por_defecto_no_hay_tope_y_todo_sigue_igual():
    assert config.MODELO_SUBE_MAX_NIVELES is None
    r = combinar(REGLAS_MEDIA, MODELO_CRITICA, "m")
    assert (r.prioridad, r.confianza) == (Prioridad.CRITICA, 0.99)


def test_con_tope_de_un_nivel_media_llega_a_alta_y_lo_dice():
    r = combinar(REGLAS_MEDIA, MODELO_CRITICA, "m", sube_max=1)
    assert r.prioridad == Prioridad.ALTA
    assert r.confianza == 0.4  # la menor de las dos: ya no es la sugerencia del modelo
    assert any("P-16" in e and Prioridad.CRITICA.value in e for e in r.evidencias)


def test_con_tope_baja_llega_a_media_con_poca_confianza_y_pide_revision():
    r = combinar(Resultado(Prioridad.BAJA, 0.5, []), MODELO_CRITICA, "m", sube_max=1)
    assert r.prioridad == Prioridad.MEDIA
    assert r.confianza < config.UMBRAL_CONFIANZA  # RN-02 la manda a «requiere revisión»


def test_el_tope_no_toca_lo_que_sube_dentro_del_limite_ni_lo_que_ven_las_reglas():
    alta = Resultado(Prioridad.ALTA, 0.8, ["señal 'sangra' -> alta"])
    r = combinar(alta, MODELO_CRITICA, "m", sube_max=1)
    assert (r.prioridad, r.confianza) == (Prioridad.CRITICA, 0.99)
    critica = Resultado(Prioridad.CRITICA, 0.9, ["señal 'convulsiona' -> crítica"])
    r = combinar(critica, Resultado(Prioridad.BAJA, 0.9, []), "m", sube_max=1)
    assert r.prioridad == Prioridad.CRITICA  # el modelo nunca baja
    assert not any("P-16" in e for e in r.evidencias)
