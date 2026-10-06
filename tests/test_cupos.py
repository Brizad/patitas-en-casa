import threading
import time
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


def test_no_alerta_por_debajo_del_umbral_de_la_linea_base():
    notificador = Mock()
    servicio = ServicioCupos(Refugio("Refugio de prueba", 40, 34), notificador)
    servicio.registrar_ingreso(animal())  # 35/40 = 87,5 % < 90 % (RF-07)
    notificador.enviar.assert_not_called()


def test_bug04_ingresos_simultaneos_no_superan_la_capacidad(monkeypatch):
    """Regresión BUG-04 (#18) / CA-20: con un solo cupo libre, solo un ingreso concurrente entra."""
    refugio = Refugio("Refugio de prueba", 40, 39)
    tiene_cupo_original = Refugio.tiene_cupo

    def tiene_cupo_lento(self):
        libre = tiene_cupo_original(self)
        time.sleep(0.1)  # amplía la ventana entre comprobar el cupo y ocuparlo
        return libre

    monkeypatch.setattr(Refugio, "tiene_cupo", tiene_cupo_lento)
    servicio = ServicioCupos(refugio, Mock())
    rechazos = []

    def ingresar():
        try:
            servicio.registrar_ingreso(animal())
        except CupoAgotado:
            rechazos.append(1)

    hilos = [threading.Thread(target=ingresar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert refugio.texto_ocupacion() == "40/40"
    assert len(rechazos) == 1


@pytest.mark.parametrize("capacidad, ocupados", [(0, 0), (10, -1), (10, 11)])
def test_bug04_refugio_rechaza_estados_invalidos(capacidad, ocupados):
    """Regresión BUG-04 (#18): capacidad 0 causaba ZeroDivisionError al calcular la ocupación."""
    with pytest.raises(ValueError):
        Refugio("Refugio de prueba", capacidad, ocupados)
