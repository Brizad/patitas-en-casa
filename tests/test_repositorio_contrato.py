"""Pruebas de contrato de RepositorioReportes (DT-01, paso 2).

Toda implementación del repositorio debe pasar exactamente las mismas pruebas: la de
memoria y la de PostgreSQL (paso 3), que usa la base de pruebas de tests/conftest.py.
"""
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioEnMemoria()


def reporte_completo(codigo="ABCD1234"):
    return Reporte(
        codigo=codigo,
        descripcion="Perro atropellado frente al parque, no se puede parar",
        ubicacion=Ubicacion(latitud=7.8939, longitud=-72.5078, direccion="Av. 0 # 10-20"),
        video_segundos=45,
        estado=EstadoReporte.CLASIFICADO,
        prioridad=Prioridad.CRITICA,
        confianza=0.8,
        evidencias=["señal 'atropellad' -> critica", "señal 'no se puede parar' -> alta"],
        creado_en=datetime(2026, 10, 14, 15, 30, 12, 123456, tzinfo=UTC),
    )


def test_guardar_y_buscar_conserva_todos_los_campos(repositorio):
    esperado = reporte_completo()
    repositorio.guardar(deepcopy(esperado))
    assert repositorio.buscar("ABCD1234") == esperado


def test_conserva_campos_vacios(repositorio):
    """Reporte recién recibido: sin GPS, sin video, sin prioridad ni evidencias."""
    esperado = Reporte(codigo="SINGPS01", descripcion="Gato con sarna en el andén del barrio",
                       ubicacion=Ubicacion(direccion="Calle 10 # 5-30"),
                       creado_en=datetime(2026, 10, 14, 9, 0, tzinfo=UTC))
    repositorio.guardar(deepcopy(esperado))
    assert repositorio.buscar("SINGPS01") == esperado


def test_buscar_codigo_inexistente_devuelve_none(repositorio):
    assert repositorio.buscar("NOEXISTE") is None


def test_repositorio_nuevo_esta_vacio(repositorio):
    assert repositorio.todos() == []


def test_todos_devuelve_cada_reporte_guardado(repositorio):
    for codigo in ("AAAA0001", "BBBB0002", "CCCC0003"):
        repositorio.guardar(reporte_completo(codigo))
    assert sorted(r.codigo for r in repositorio.todos()) == ["AAAA0001", "BBBB0002", "CCCC0003"]


def test_guardar_el_mismo_codigo_actualiza_sin_duplicar(repositorio):
    """El veterinario confirma la prioridad: el reporte se vuelve a guardar con otro estado."""
    reporte = reporte_completo()
    repositorio.guardar(deepcopy(reporte))
    reporte.estado = EstadoReporte.CONFIRMADO
    reporte.prioridad = Prioridad.ALTA
    repositorio.guardar(deepcopy(reporte))
    assert len(repositorio.todos()) == 1
    guardado = repositorio.buscar("ABCD1234")
    assert (guardado.estado, guardado.prioridad) == (EstadoReporte.CONFIRMADO, Prioridad.ALTA)
