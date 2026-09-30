from unittest.mock import Mock

import pytest

from app.cupos.servicio import CupoAgotado, ServicioCupos
from app.dominio.modelos import Animal, Especie, Refugio


def animal():
    return Animal(nombre="Luna", especie=Especie.PERRO, estado_salud="herida en pata")


def test_ingreso_actualiza_ocupacion():
    servicio = ServicioCupos(Refugio("Refugio de prueba", 40, 35), Mock())
    servicio.registrar_ingreso(animal())
    assert servicio.texto_ocupacion() == "36/40"


def test_alerta_al_llegar_al_umbral():
    notificador = Mock()
    servicio = ServicioCupos(Refugio("Refugio de prueba", 40, 35), notificador)
    servicio.registrar_ingreso(animal())  # 36/40 = 90 %
    notificador.enviar.assert_called_once()


def test_sin_cupos_rechaza_ingreso():
    servicio = ServicioCupos(Refugio("Refugio de prueba", 2, 2), Mock())
    with pytest.raises(CupoAgotado):
        servicio.registrar_ingreso(animal())


def test_ficha_incompleta_no_se_guarda():
    servicio = ServicioCupos(Refugio("Refugio de prueba", 10, 0), Mock())
    with pytest.raises(ValueError):
        servicio.registrar_ingreso(Animal(nombre="", especie=Especie.GATO, estado_salud=""))
