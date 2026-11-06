"""TDD (Guía 8, FPI-24): percentil por rango más cercano de la prueba de carga (RNF-01)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "operacion"))
from prueba_carga import percentil  # noqa: E402

DIEZ = [float(x) for x in range(1, 11)]


def test_p95_de_veinte_valores_es_el_decimonoveno():
    assert percentil([float(x) for x in range(1, 21)], 95) == 19


def test_percentiles_bajos_no_devuelven_el_maximo():
    assert percentil(DIEZ, 1) == 1
    assert percentil(DIEZ, 5) == 1


def test_p100_es_el_maximo_y_no_depende_del_orden():
    assert percentil(list(reversed(DIEZ)), 100) == 10


def test_lista_vacia_da_error_claro():
    with pytest.raises(ValueError, match="sin mediciones"):
        percentil([], 95)


@pytest.mark.parametrize("p", [0, -1, 101])
def test_percentil_fuera_de_rango(p):
    with pytest.raises(ValueError):
        percentil(DIEZ, p)
