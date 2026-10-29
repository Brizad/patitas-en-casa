"""Tubería del análisis (#125): cuadros → animal → puntos → marcha → prioridad, con dobles."""
import pytest
from patitas_video.analisis import Caja, analizar
from patitas_video.clasificador import ClasificadorMarcha

from tests.trayectorias_video import caminar


class Lector:
    def __init__(self, cuadros):
        self._cuadros = cuadros

    def cuadros(self, _ruta, _fps):
        yield from self._cuadros


class Detector:
    def __init__(self, especie="dog"):
        self.especie = especie

    def detectar(self, imagen):
        return None if imagen is None else Caja(0, 0, 100, 100, self.especie, 0.9)


class Estimador:
    def puntos(self, imagen, _caja):
        return imagen  # en la prueba, la «imagen» ya son los puntos


class Dibujante:
    def tira(self, muestras):
        return b"\x89PNG" + bytes([len(muestras)])


@pytest.fixture(scope="module")
def clasificador():
    return ClasificadorMarcha.desde_json()


def test_la_tuberia_da_prioridad_evidencias_y_tira_de_tres_cuadros(clasificador):
    r = analizar("v", Lector(caminar(levantada="back_left_paw")), Detector(), Estimador(),
                 clasificador, Dibujante())
    assert r["prioridad"] in ("alta", "critica")
    assert r["evidencias"][0] == "se ve un perro en el 100 % del video"
    assert len(r["evidencias"]) >= 4
    assert r["tira"] == b"\x89PNG\x03"
    assert r["version_modelo"] == "marcha-mlp-v1"


def test_sin_perro_ni_gato_no_es_concluyente(clasificador):
    sin_animal = analizar("v", Lector([None] * 50), Detector(), Estimador(), clasificador)
    assert sin_animal["prioridad"] is None
    assert "no se ve un perro o un gato" in sin_animal["motivo"]
    persona = analizar("v", Lector(caminar()), Detector("person"), Estimador(), clasificador)
    assert persona["prioridad"] is None
    vacio = analizar("v", Lector([]), Detector(), Estimador(), clasificador)
    assert vacio["motivo"] == "no se pudo leer el video"


def test_puntos_poco_confiables_no_son_concluyentes(clasificador):
    borrosos = [{k: (x, y, 0.1) for k, (x, y, _c) in c.items()} for c in caminar()]
    r = analizar("v", Lector(borrosos), Detector(), Estimador(), clasificador)
    assert r["prioridad"] is None
    assert "cuerpo completo" in r["motivo"]
