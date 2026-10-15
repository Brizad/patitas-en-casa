"""Contrato de RepositorioRescates (HU-06, RN-08): memoria y PostgreSQL cumplen lo mismo."""
import threading
from datetime import UTC, datetime

import pytest

from app.dominio.modelos import (
    EstadoReporte,
    EstadoRescate,
    Prioridad,
    Reporte,
    ResultadoRescate,
    Ubicacion,
)
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.rescates.repositorio import (
    RepositorioRescatesEnMemoria,
    RescateTomado,
    RescatistaOcupado,
)
from app.rescates.repositorio_postgres import RepositorioRescatesPostgres

MOMENTO = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)
ANA, LUIS = "ana@rescate.co", "luis@rescate.co"


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        motor = request.getfixturevalue("bd_limpia")
        reportes = RepositorioPostgres(motor)  # en la base el rescate exige un reporte real
        for codigo in ("AAAA0001", "BBBB0002"):
            reportes.guardar(Reporte(codigo=codigo, descripcion="Perro atropellado en la vía",
                                     ubicacion=Ubicacion(direccion="Calle 10"),
                                     estado=EstadoReporte.CONFIRMADO,
                                     prioridad=Prioridad.CRITICA))
        return RepositorioRescatesPostgres(motor)
    return RepositorioRescatesEnMemoria()


def test_disponibilidad_por_defecto_es_no_y_se_puede_cambiar(repositorio):
    assert repositorio.esta_disponible(ANA) is False
    repositorio.poner_disponible(ANA, True)
    assert repositorio.esta_disponible(ANA) is True
    repositorio.poner_disponible(ANA, False)
    assert repositorio.esta_disponible(ANA) is False


def test_aceptar_deja_el_rescate_en_camino(repositorio):
    rescate = repositorio.aceptar("AAAA0001", ANA, MOMENTO)
    assert (rescate.codigo, rescate.rescatista, rescate.estado) == (
        "AAAA0001", ANA, EstadoRescate.EN_CAMINO)
    assert repositorio.vigente("AAAA0001") == rescate
    assert repositorio.activo_de(ANA) == rescate
    assert repositorio.codigos_tomados() == {"AAAA0001"}


def test_rn08_un_rescate_tiene_un_solo_rescatista(repositorio):
    repositorio.aceptar("AAAA0001", ANA, MOMENTO)
    with pytest.raises(RescateTomado):
        repositorio.aceptar("AAAA0001", LUIS, MOMENTO)


def test_rn08_un_rescatista_tiene_un_solo_rescate_activo(repositorio):
    repositorio.aceptar("AAAA0001", ANA, MOMENTO)
    with pytest.raises(RescatistaOcupado):
        repositorio.aceptar("BBBB0002", ANA, MOMENTO)


def test_avanzar_solo_desde_el_estado_esperado_y_por_su_rescatista(repositorio):
    repositorio.aceptar("AAAA0001", ANA, MOMENTO)
    assert repositorio.avanzar("AAAA0001", LUIS, EstadoRescate.EN_CAMINO,
                               EstadoRescate.EN_SITIO, MOMENTO) is False
    assert repositorio.avanzar("AAAA0001", ANA, EstadoRescate.EN_SITIO,
                               EstadoRescate.ATENDIDO, MOMENTO) is False
    assert repositorio.avanzar("AAAA0001", ANA, EstadoRescate.EN_CAMINO,
                               EstadoRescate.EN_SITIO, MOMENTO) is True
    assert repositorio.vigente("AAAA0001").estado == EstadoRescate.EN_SITIO


def test_liberar_devuelve_el_rescate_a_las_ofertas(repositorio):
    repositorio.aceptar("AAAA0001", ANA, MOMENTO)
    repositorio.avanzar("AAAA0001", ANA, EstadoRescate.EN_CAMINO, EstadoRescate.LIBERADO,
                        MOMENTO)
    assert repositorio.vigente("AAAA0001") is None
    assert repositorio.activo_de(ANA) is None
    assert repositorio.codigos_tomados() == set()
    assert repositorio.aceptar("AAAA0001", LUIS, MOMENTO).rescatista == LUIS


def test_resultado_cierra_el_rescate_y_libera_al_rescatista(repositorio):
    repositorio.aceptar("AAAA0001", ANA, MOMENTO)
    repositorio.avanzar("AAAA0001", ANA, EstadoRescate.EN_CAMINO, EstadoRescate.EN_SITIO,
                        MOMENTO)
    repositorio.avanzar("AAAA0001", ANA, EstadoRescate.EN_SITIO, EstadoRescate.ATENDIDO,
                        MOMENTO, ResultadoRescate.TRASLADADO)
    cerrado = repositorio.vigente("AAAA0001")
    assert (cerrado.estado, cerrado.resultado) == (EstadoRescate.ATENDIDO,
                                                   ResultadoRescate.TRASLADADO)
    assert repositorio.activo_de(ANA) is None
    assert repositorio.codigos_tomados() == {"AAAA0001"}  # atendido: ya no se ofrece
    assert repositorio.aceptar("BBBB0002", ANA, MOMENTO).estado == EstadoRescate.EN_CAMINO


def _a_la_vez(*acciones):
    salida = threading.Barrier(len(acciones))
    resultados = []

    def correr(accion):
        salida.wait()
        try:
            accion()
            resultados.append("ok")
        except (RescateTomado, RescatistaOcupado) as error:
            resultados.append(type(error).__name__)

    hilos = [threading.Thread(target=correr, args=(a,)) for a in acciones]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return sorted(resultados)


def test_rn08_dos_rescatistas_aceptando_a_la_vez(repositorio):
    resultados = _a_la_vez(lambda: repositorio.aceptar("AAAA0001", ANA, MOMENTO),
                           lambda: repositorio.aceptar("AAAA0001", LUIS, MOMENTO))
    assert resultados == ["RescateTomado", "ok"]


def test_rn08_un_rescatista_aceptando_dos_rescates_a_la_vez(repositorio):
    resultados = _a_la_vez(lambda: repositorio.aceptar("AAAA0001", ANA, MOMENTO),
                           lambda: repositorio.aceptar("BBBB0002", ANA, MOMENTO))
    assert resultados == ["RescatistaOcupado", "ok"]
