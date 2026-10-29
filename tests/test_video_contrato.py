"""Contrato de RepositorioVideos (#125): lo que cualquier versión (memoria o PostgreSQL) cumple."""
from datetime import UTC, datetime, timedelta

import pytest

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.video.modelos import EstadoVideo
from app.video.repositorio import RepositorioVideosEnMemoria
from app.video.repositorio_postgres import RepositorioVideosPostgres

T0 = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repo(request):
    if request.param == "memoria":
        return RepositorioVideosEnMemoria()
    motor = request.getfixturevalue("bd_limpia")
    reportes = RepositorioPostgres(motor)
    for codigo in ("ABCD1234", "BBBB2222", "CCCC3333"):
        reportes.guardar(Reporte(codigo, "Perro cojeando cerca del parque",
                                 Ubicacion(direccion="Calle 10")))
    return RepositorioVideosPostgres(motor)


def test_un_video_por_reporte(repo):
    trabajo = repo.crear("ABCD1234", "/tmp/a.mp4", 1000, T0)
    assert (trabajo.estado, trabajo.intentos, trabajo.bytes) == (EstadoVideo.PENDIENTE, 0, 1000)
    assert repo.crear("ABCD1234", "/tmp/b.mp4", 1000, T0) is None
    assert repo.de_reporte("ABCD1234").ruta == "/tmp/a.mp4"
    assert repo.de_reporte("ZZZZ9999") is None


def test_reclamar_da_el_mas_antiguo_una_sola_vez_y_retoma_los_vencidos(repo):
    repo.crear("BBBB2222", "/tmp/b.mp4", 1, T0 + timedelta(minutes=1))
    repo.crear("ABCD1234", "/tmp/a.mp4", 1, T0)
    primero = repo.reclamar(T0, T0 - timedelta(minutes=10))
    assert (primero.codigo, primero.estado, primero.reclamado_en) == (
        "ABCD1234", EstadoVideo.ENVIADO, T0)
    assert repo.reclamar(T0, T0 - timedelta(minutes=10)).codigo == "BBBB2222"
    assert repo.reclamar(T0, T0 - timedelta(minutes=10)) is None
    # Diez minutos después, los reclamos de T0 vencieron: se vuelven a dar.
    assert repo.reclamar(T0 + timedelta(minutes=11), T0 + timedelta(minutes=1)).codigo == \
        "ABCD1234"


def test_guardar_conserva_el_resultado(repo):
    trabajo = repo.crear("ABCD1234", "/tmp/a.mp4", 1, T0)
    trabajo.estado, trabajo.prioridad, trabajo.confianza = (
        EstadoVideo.TERMINADO, Prioridad.ALTA, 0.8)
    trabajo.evidencias, trabajo.medidas, trabajo.tira = ["no apoya"], {"de_pie": 0.9}, b"png"
    trabajo.discrepancia, trabajo.terminado_en = True, T0
    repo.guardar(trabajo)
    leido = repo.buscar(trabajo.id)
    assert (leido.estado, leido.prioridad, leido.evidencias, leido.medidas, leido.tira,
            leido.discrepancia) == (EstadoVideo.TERMINADO, Prioridad.ALTA, ["no apoya"],
                                    {"de_pie": 0.9}, b"png", True)
    assert repo.buscar(999) is None


def test_esperando_desde_antes_solo_cuenta_lo_que_no_termino(repo):
    viejo = repo.crear("ABCD1234", "/tmp/a.mp4", 1, T0)
    repo.crear("BBBB2222", "/tmp/b.mp4", 1, T0 + timedelta(hours=5))
    terminado = repo.crear("CCCC3333", "/tmp/c.mp4", 1, T0)
    terminado.estado = EstadoVideo.TERMINADO
    repo.guardar(terminado)
    assert [t.id for t in repo.esperando_desde_antes(T0 + timedelta(hours=1))] == [viejo.id]


@pytest.mark.postgres
def test_actualizar_triaje_no_deshace_la_decision_del_veterinario(bd_limpia):
    reportes = RepositorioPostgres(bd_limpia)
    reporte = Reporte("ABCD1234", "Perro cojeando cerca del parque",
                      Ubicacion(direccion="Calle 10"), estado=EstadoReporte.REQUIERE_REVISION,
                      prioridad=Prioridad.MEDIA, confianza=0.5)
    reportes.guardar(reporte)
    reporte.prioridad, reporte.estado = Prioridad.ALTA, EstadoReporte.CLASIFICADO
    reporte.evidencias = ["video: no apoya la pata"]
    assert reportes.actualizar_triaje(reporte) is True
    leido = reportes.buscar("ABCD1234")
    assert (leido.prioridad, leido.evidencias) == (Prioridad.ALTA, ["video: no apoya la pata"])
    reportes.guardar(Reporte("ABCD1234", reporte.descripcion, reporte.ubicacion,
                             estado=EstadoReporte.CONFIRMADO, prioridad=Prioridad.MEDIA))
    assert reportes.actualizar_triaje(reporte) is False
    assert reportes.buscar("ABCD1234").prioridad == Prioridad.MEDIA
