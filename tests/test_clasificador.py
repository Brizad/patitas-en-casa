import pytest

from app.dominio.modelos import Prioridad
from app.triaje.clasificador import clasificar


def test_atropellado_es_critico():
    r = clasificar("encontré un perro atropellado en la avenida, está sangrando")
    assert r.prioridad == Prioridad.CRITICA
    assert any("atropellad" in e for e in r.evidencias)


def test_negacion_descarta_senal():
    r = clasificar("el gato tiene una herida pequeña pero no sangra y camina bien")
    assert r.prioridad == Prioridad.ALTA  # la herida sigue contando
    assert not any("sangr" in e for e in r.evidencias)


def test_sin_senales_devuelve_baja_con_confianza_baja():
    r = clasificar("hay un perrito en el parque del barrio")
    assert r.prioridad == Prioridad.BAJA
    assert r.confianza < 0.6


def test_confianza_crece_con_senales_del_mismo_nivel():
    una = clasificar("perro atropellado")
    dos = clasificar("perro atropellado, está inconsciente")
    assert dos.confianza > una.confianza


def test_bug01_senales_con_tilde_se_detectan():
    """Regresión BUG-01: 'convulsión' y 'vómito' con tilde no se detectaban."""
    r = clasificar("El perro tuvo una convulsión y después vómito con sangre")
    assert r.prioridad == Prioridad.CRITICA
    assert any("convulsion" in e for e in r.evidencias)


@pytest.mark.parametrize("texto", [
    "el perro del vecino atropellado en la calle",
    "un gato atropellado en el camino",
    "un perrito pequeño atropellado",
])
def test_bug02_palabras_terminadas_en_no_no_niegan_la_senal(texto):
    """Regresión BUG-02 (#16): 'vecino', 'camino' o 'pequeño' no son la palabra 'no'."""
    r = clasificar(texto)
    assert r.prioridad == Prioridad.CRITICA


def test_bug02_senal_repetida_cuenta_si_una_aparicion_no_esta_negada():
    """Regresión BUG-02 (#16): antes solo se revisaba la primera aparición de la señal."""
    r = clasificar("no sangra por la boca, pero sí sangra mucho por la pata")
    assert any("sangr" in e for e in r.evidencias)
