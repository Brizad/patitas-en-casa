"""RN-01: la descripción debe estar escrita con palabras (#225)."""
import pytest

from app.dominio.modelos import Ubicacion
from app.reportes.descripcion import MENSAJE, descripcion_con_sentido
from app.reportes.servicio import ReporteInvalido, ServicioReportes


@pytest.mark.parametrize("texto", [
    "perro atropellado no se levanta y sangra",
    "Perro atropellado, no se levanta y sangra mucho",
    "El perro se está muriendo, porque le grabaron un titkok",
    "gato con la pata rota en la calle",
    "perro con garrapatas y muy flaco",
    "cachorro abandonado bajo la lluvia ayer",
    "perro herido en el parque de Cúcuta",
])
def test_descripciones_reales_se_aceptan(texto):
    assert descripcion_con_sentido(texto)


@pytest.mark.parametrize("texto", [
    "Jsjsisoslqmwnabsnsnans",
    "Eksowpwpwowowowlwkksksks",
    "Jsjsisoslqmwnabsnsnans Eksowpwpwowowowlwkksksks",  # solo 2 palabras
    "asdfg hjklñ qwert zxcvb poiuy",  # 5 palabras, casi sin vocales
    "aaaa eeee oooo iiii uuuu",  # solo vocales
    "1234567890 1234567890 1234567890",
    "..................... ..... .....",
])
def test_descripciones_sin_sentido_se_rechazan(texto):
    assert not descripcion_con_sentido(texto)


def test_limite_de_palabras_tres_no_y_cuatro_si():
    assert not descripcion_con_sentido("perro herido grave")  # 3 palabras
    assert descripcion_con_sentido("perro herido muy grave")  # 4 palabras


def test_palabras_de_una_letra_no_cuentan():
    assert not descripcion_con_sentido("perro herido y a e")  # solo 2 de 2 letras o más
    assert descripcion_con_sentido("perro herido y no se mueve")


def test_limites_de_la_proporcion_de_vocales():
    # 3 de 10 letras = 30 %: justo en el límite inferior (se acepta)
    assert descripcion_con_sentido("aaabbbbbbb aaabbbbbbb aaabbbbbbb aaabbbbbbb")
    # 2 de 10 = 20 %: por debajo
    assert not descripcion_con_sentido("aabbbbbbbb aabbbbbbbb aabbbbbbbb aabbbbbbbb")
    # 7 de 10 = 70 %: justo en el límite superior (se acepta)
    assert descripcion_con_sentido("aaaeeeebbb aaaeeeebbb aaaeeeebbb aaaeeeebbb")
    # 8 de 10 = 80 %: por encima
    assert not descripcion_con_sentido("aaaeeeeebb aaaeeeeebb aaaeeeeebb aaaeeeeebb")


class _Triaje:
    def evaluar(self, reporte):
        pass


class _Repo:
    def buscar(self, codigo):
        return None

    def guardar(self, reporte):
        pass


def test_el_servicio_rechaza_el_texto_sin_sentido_con_mensaje_claro():
    servicio = ServicioReportes(_Repo(), _Triaje())
    with pytest.raises(ReporteInvalido, match=MENSAJE):
        servicio.registrar("Eksowpwpwowowowlwkksksks", Ubicacion(direccion="Calle 10 #5-20"))
