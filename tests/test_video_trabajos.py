"""Trabajos de video en Render (#125): subida, reclamo, resultado, fallos y falla segura."""
from datetime import UTC, datetime, timedelta

import pytest

from app import config
from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.video.modelos import EstadoVideo, ResultadoVideo
from app.video.repositorio import RepositorioVideosEnMemoria
from app.video.servicio import ServicioVideo, VideoRechazado

CLAVE = "clave-del-telefono-0001"
INICIO = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
VIDEO_ALTA = ResultadoVideo(Prioridad.ALTA, 0.8, ["no apoya la pata trasera izquierda",
                                                  "se mantiene de pie en el 90 % de los cuadros",
                                                  "cojea"], {"asimetria": 0.7}, "marcha-mlp-v1",
                            tira=b"\x89PNG")


class AlmacenFalso:
    def __init__(self):
        self.archivos = set()

    def existe(self, ruta):
        return ruta in self.archivos

    def borrar(self, ruta):
        self.archivos.discard(ruta)


class Reloj:
    def __init__(self):
        self.ahora = INICIO

    def __call__(self):
        return self.ahora


@pytest.fixture
def entorno():
    reportes, almacen, reloj = RepositorioEnMemoria(), AlmacenFalso(), Reloj()
    reportes.guardar_con_clave(Reporte(
        "ABCD1234", "Perro cojeando cerca del parque", Ubicacion(direccion="Calle 10"),
        estado=EstadoReporte.REQUIERE_REVISION, prioridad=Prioridad.MEDIA, confianza=0.5,
        evidencias=["señal 'cojea' -> media"], creado_en=INICIO), CLAVE)
    servicio = ServicioVideo(RepositorioVideosEnMemoria(), reportes, almacen, reloj)
    return servicio, reportes, almacen, reloj


def subir(servicio, almacen, ruta="/tmp/v1.mp4"):
    servicio.autorizar_subida("ABCD1234", CLAVE)
    almacen.archivos.add(ruta)
    return servicio.registrar("ABCD1234", ruta, 1000)


def test_solo_quien_creo_el_reporte_sube_el_video_a_tiempo_y_una_vez(entorno):
    servicio, _, almacen, reloj = entorno
    for clave in (None, "otra-clave-cualquiera-1"):
        with pytest.raises(VideoRechazado) as error:
            servicio.autorizar_subida("ABCD1234", clave)
        assert error.value.estado_http == 403
    subir(servicio, almacen)
    with pytest.raises(VideoRechazado) as error:
        servicio.autorizar_subida("ABCD1234", CLAVE)
    assert error.value.estado_http == 409
    reloj.ahora += timedelta(minutes=config.VIDEO_VENTANA_SUBIDA_MINUTOS + 1)
    with pytest.raises(VideoRechazado):
        servicio.autorizar_subida("ABCD1234", CLAVE)


def test_si_dos_subidas_compiten_la_segunda_se_borra(entorno):
    servicio, _, almacen, _ = entorno
    subir(servicio, almacen)
    almacen.archivos.add("/tmp/v2.mp4")
    with pytest.raises(VideoRechazado):
        servicio.registrar("ABCD1234", "/tmp/v2.mp4", 1000)
    assert almacen.archivos == {"/tmp/v1.mp4"}


def test_rn07_el_video_mas_grave_sube_la_prioridad_y_rf19_registra_la_discrepancia(entorno):
    servicio, reportes, almacen, _ = entorno
    subir(servicio, almacen)
    trabajo = servicio.reclamar()
    assert servicio.reclamar() is None  # nadie más lo recibe
    assert servicio.ruta_para_descargar(trabajo.id) == "/tmp/v1.mp4"
    hecho = servicio.terminar(trabajo.id, VIDEO_ALTA)
    assert (hecho.estado, hecho.discrepancia) == (EstadoVideo.TERMINADO, True)
    reporte = reportes.buscar("ABCD1234")
    assert (reporte.prioridad, reporte.estado) == (Prioridad.ALTA, EstadoReporte.CLASIFICADO)
    assert "video: no apoya la pata trasera izquierda" in reporte.evidencias
    assert almacen.archivos == set()  # RNF-08: el video se borró


def test_lo_que_ya_decidio_el_veterinario_no_cambia(entorno):
    servicio, reportes, almacen, _ = entorno
    subir(servicio, almacen)
    reportes.buscar("ABCD1234").estado = EstadoReporte.CONFIRMADO
    servicio.terminar(servicio.reclamar().id, VIDEO_ALTA)
    assert reportes.buscar("ABCD1234").prioridad == Prioridad.MEDIA


def test_video_no_concluyente_manda_el_texto(entorno):
    servicio, reportes, almacen, _ = entorno
    subir(servicio, almacen)
    trabajo = servicio.terminar(servicio.reclamar().id, ResultadoVideo(
        None, 0.0, [], motivo="no se ve un perro ni un gato"))
    assert (trabajo.estado, trabajo.motivo) == (EstadoVideo.NO_CONCLUYENTE,
                                                "no se ve un perro ni un gato")
    assert reportes.buscar("ABCD1234").prioridad == Prioridad.MEDIA
    assert almacen.archivos == set()


def test_un_video_perdido_por_reinicio_queda_fallido(entorno):
    servicio, _, almacen, _ = entorno
    subir(servicio, almacen)
    trabajo = servicio.reclamar()
    almacen.archivos.clear()  # Render se reinició y borró el disco
    with pytest.raises(VideoRechazado) as error:
        servicio.ruta_para_descargar(trabajo.id)
    assert error.value.estado_http == 410
    assert servicio.reclamar() is None


def test_los_fallos_se_reintentan_hasta_agotar_los_intentos(entorno):
    servicio, _, almacen, _ = entorno
    subir(servicio, almacen)
    for _ in range(config.MAX_INTENTOS_VIDEO - 1):
        assert servicio.fallar(servicio.reclamar().id, "sin memoria").estado == \
            EstadoVideo.PENDIENTE
    assert servicio.fallar(servicio.reclamar().id, "sin memoria").estado == EstadoVideo.FALLIDO
    assert almacen.archivos == set()
    with pytest.raises(VideoRechazado) as error:  # un resultado tardío ya no se acepta
        servicio.terminar(1, VIDEO_ALTA)
    assert error.value.estado_http == 409


def test_un_reclamo_vencido_se_le_da_a_otro_trabajador(entorno):
    servicio, _, almacen, reloj = entorno
    subir(servicio, almacen)
    primero = servicio.reclamar()
    reloj.ahora += timedelta(seconds=config.VENCIMIENTO_RECLAMO_VIDEO_S + 1)
    assert servicio.reclamar().id == primero.id


def test_si_el_trabajador_estuvo_apagado_el_video_vence_y_se_borra(entorno):
    servicio, _, almacen, reloj = entorno
    subir(servicio, almacen)
    assert servicio.revisar() == 0
    reloj.ahora += timedelta(hours=config.VIDEO_MAX_ESPERA_HORAS, minutes=1)
    assert servicio.revisar() == 1
    assert almacen.archivos == set()
    assert servicio.reclamar() is None
