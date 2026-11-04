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


class EscritorFalso:
    def __init__(self, falla_en=None):
        self.cuadros, self.falla_en, self.cancelado = [], falla_en, False

    def escribir(self, _imagen, puntos):
        if self.falla_en is not None and len(self.cuadros) == self.falla_en:
            raise OSError("ffmpeg murió")
        self.cuadros.append(puntos)

    def terminar(self):
        return b"\x00\x00\x00\x18ftypmp42"

    def cancelar(self):
        self.cancelado = True


def test_la_vista_previa_recibe_todos_los_cuadros_y_viaja_en_el_resultado(clasificador):
    cuadros = [None] * 4 + caminar(levantada="back_left_paw")
    escritor = EscritorFalso()
    r = analizar("v", Lector(cuadros), Detector(), Estimador(), clasificador,
                 escritor_vista=escritor)
    assert len(escritor.cuadros) == len(cuadros)  # también los cuadros sin animal
    assert escritor.cuadros[:4] == [None] * 4  # sin animal: se escribe sin esqueleto
    assert r["vista"].startswith(b"\x00\x00\x00\x18ftyp")


def test_la_vista_tambien_se_entrega_si_el_resultado_no_es_concluyente(clasificador):
    r = analizar("v", Lector([None] * 50), Detector(), Estimador(), clasificador,
                 escritor_vista=EscritorFalso())
    assert r["prioridad"] is None
    assert "vista" in r


def test_si_la_vista_falla_el_analisis_sigue_sin_ella(clasificador):
    escritor = EscritorFalso(falla_en=3)
    r = analizar("v", Lector(caminar(levantada="back_left_paw")), Detector(), Estimador(),
                 clasificador, escritor_vista=escritor)
    assert r["prioridad"] in ("alta", "critica")  # la vista es opcional: no rompe el triaje
    assert "vista" not in r
    assert escritor.cancelado


class EscritorQueNoTermina(EscritorFalso):
    def terminar(self):
        return None  # ffmpeg falló o la vista pasó de 5 MB


def test_regresion_231_sin_ffmpeg_el_resultado_dice_por_que_no_hay_vista(clasificador):
    r = analizar("v", Lector([None] * 5), Detector(), Estimador(), clasificador)
    assert "vista" not in r
    assert "ffmpeg" in r["sin_vista"]


def test_regresion_231_si_ffmpeg_no_entrega_el_mp4_tambien_se_dice(clasificador):
    r = analizar("v", Lector([None] * 5), Detector(), Estimador(), clasificador,
                 escritor_vista=EscritorQueNoTermina())
    assert "vista" not in r and r["sin_vista"]


def test_regresion_231_un_video_ilegible_no_tiene_vista_y_lo_dice(clasificador):
    r = analizar("v", Lector([]), Detector(), Estimador(), clasificador,
                 escritor_vista=EscritorQueNoTermina())
    assert r["motivo"] == "no se pudo leer el video"
    assert "cuadro" in r["sin_vista"]


def test_con_vista_no_hay_motivo_de_ausencia(clasificador):
    r = analizar("v", Lector([None] * 5), Detector(), Estimador(), clasificador,
                 escritor_vista=EscritorFalso())
    assert "vista" in r and "sin_vista" not in r
