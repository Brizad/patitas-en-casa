import pytest

from app.dominio.modelos import Prioridad, Ubicacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.servicio import ReporteInvalido, ServicioReportes
from app.triaje.clasificador import Resultado
from app.triaje.servicio import ServicioTriaje

TEXTO = "Perro atropellado frente al parque, no se puede parar"


def servicio():
    triaje = ServicioTriaje(clasificador=lambda _t: Resultado(Prioridad.CRITICA, 0.8, ["stub"]))
    return ServicioReportes(RepositorioEnMemoria(), triaje)


def test_reporte_sin_cuenta_devuelve_codigo_de_8_caracteres():
    r = servicio().registrar(TEXTO, Ubicacion(latitud=7.89, longitud=-72.50))
    assert len(r.codigo) == 8 and r.codigo.isalnum()


def test_descripcion_corta_se_rechaza():
    with pytest.raises(ReporteInvalido):
        servicio().registrar("perro herido", Ubicacion(direccion="Calle 10"))


def test_sin_ubicacion_se_rechaza():
    with pytest.raises(ReporteInvalido):
        servicio().registrar(TEXTO, Ubicacion())


@pytest.mark.parametrize("segundos, aceptado", [(59, True), (60, True), (61, False), (75, False)])
def test_limite_de_duracion_del_video(segundos, aceptado):
    s = servicio()
    if aceptado:
        assert s.registrar(TEXTO, Ubicacion(direccion="Calle 10"), video_segundos=segundos)
    else:
        with pytest.raises(ReporteInvalido, match="60 segundos"):
            s.registrar(TEXTO, Ubicacion(direccion="Calle 10"), video_segundos=segundos)
