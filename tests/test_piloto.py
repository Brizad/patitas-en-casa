"""Modo piloto de usabilidad (RNF-06, #258)."""
from datetime import UTC, datetime, timedelta

import pytest

from app.piloto.repositorio_postgres import RepositorioPilotoPostgres
from app.piloto.servicio import RepositorioPilotoEnMemoria, ServicioPiloto, puntaje_sus
from scripts.operacion.resultados_piloto import calcular

TEXTO = "Perro atropellado frente al parque Santander, no se levanta y sangra"
REPORTE = {"descripcion": TEXTO, "direccion": "Parque Santander, Cúcuta"}
SUS = [4, 2, 5, 1, 4, 2, 5, 1, 4, 2]  # SUS = 85


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioPilotoPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioPilotoEnMemoria()


def test_flujo_completo_participante_anonimo_reporta_y_responde(repositorio):
    servicio = ServicioPiloto(repositorio)
    p1, token = servicio.invitar()
    p2, _ = servicio.invitar()
    assert (p1.codigo, p2.codigo) == ("P01", "P02")
    from app.dominio.modelos import Ubicacion
    codigo = servicio.reportar(token, TEXTO, Ubicacion(direccion="Calle 10"))
    assert len(codigo) == 8
    servicio.responder(token, 62, SUS)
    assert [p.codigo for p in servicio.completos()] == ["P01"]
    assert servicio.invitados() == 2
    assert repositorio.todos()[0].sus == SUS and repositorio.todos()[0].segundos == 62


def test_el_csv_lo_lee_el_script_del_piloto():
    servicio = ServicioPiloto(RepositorioPilotoEnMemoria())
    from app.dominio.modelos import Ubicacion
    for segundos in (62, 120):
        _, token = servicio.invitar()
        servicio.reportar(token, TEXTO, Ubicacion(direccion="Calle 10"))
        servicio.responder(token, segundos, SUS)
    resultado = calcular(servicio.csv())
    assert (resultado.participantes, resultado.cumplen_tiempo) == (2, 1)
    assert resultado.sus_promedio == puntaje_sus(SUS) == 85


def test_token_vencido_usado_o_falso_se_rechaza():
    ahora = [datetime(2026, 11, 5, tzinfo=UTC)]
    servicio = ServicioPiloto(RepositorioPilotoEnMemoria(), reloj=lambda: ahora[0])
    from app.dominio.modelos import Ubicacion
    from app.piloto.servicio import PilotoRechazado
    _, token = servicio.invitar()
    with pytest.raises(PilotoRechazado, match="Primero envía"):
        servicio.responder(token, 30, SUS)
    servicio.reportar(token, TEXTO, Ubicacion(direccion="Calle 10"))
    servicio.responder(token, 30, SUS)
    with pytest.raises(PilotoRechazado) as usado:
        servicio.responder(token, 30, SUS)
    assert usado.value.estado_http == 409
    _, otro = servicio.invitar()
    ahora[0] += timedelta(hours=25)
    with pytest.raises(PilotoRechazado) as vencido:
        servicio.reportar(otro, TEXTO, Ubicacion(direccion="Calle 10"))
    assert vencido.value.estado_http == 403
    with pytest.raises(PilotoRechazado):
        servicio.reportar("token-inventado", TEXTO, Ubicacion(direccion="Calle 10"))
