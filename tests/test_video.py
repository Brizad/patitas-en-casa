"""RF-19, RN-07 (#95): fusión texto + video; el adaptador real queda como deuda (DT-10)."""
import pytest

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.triaje.clasificador import Resultado
from app.triaje.video import AnalizadorNoDisponible, VideoNoDisponible, aplicar_video, fusionar

TEXTO_MEDIA = Resultado(Prioridad.MEDIA, 0.55, ["señal 'cojea' -> media"])
VIDEO_ALTA = Resultado(Prioridad.ALTA, 0.8, ["no apoya la pata trasera izquierda"])


def reporte(estado=EstadoReporte.REQUIERE_REVISION):
    return Reporte(codigo="ABCD1234", descripcion="Perro cojeando cerca del parque",
                   ubicacion=Ubicacion(direccion="Calle 10"), prioridad=Prioridad.MEDIA,
                   confianza=0.55, evidencias=["señal 'cojea' -> media"], estado=estado)


def test_rn07_gana_la_prioridad_mas_alta_y_se_juntan_las_evidencias():
    r = fusionar(TEXTO_MEDIA, VIDEO_ALTA)
    assert (r.prioridad, r.confianza) == (Prioridad.ALTA, 0.8)
    assert r.evidencias == ["señal 'cojea' -> media", "video: no apoya la pata trasera izquierda"]
    assert fusionar(VIDEO_ALTA, TEXTO_MEDIA).prioridad == Prioridad.ALTA  # simétrico
    assert fusionar(TEXTO_MEDIA, None) is TEXTO_MEDIA


def test_el_video_sube_un_reporte_pendiente_y_lo_saca_de_revision():
    r = reporte()
    assert aplicar_video(r, VIDEO_ALTA) is True
    assert (r.prioridad, r.estado) == (Prioridad.ALTA, EstadoReporte.CLASIFICADO)


def test_el_video_nunca_baja_ni_toca_lo_que_decidio_una_persona():
    r = reporte()
    assert aplicar_video(r, Resultado(Prioridad.BAJA, 0.9, [])) is False
    assert r.prioridad == Prioridad.MEDIA
    confirmado = reporte(EstadoReporte.CONFIRMADO)
    assert aplicar_video(confirmado, VIDEO_ALTA) is False
    assert confirmado.prioridad == Prioridad.MEDIA


def test_sin_worker_el_analizador_lo_dice_claramente():
    with pytest.raises(VideoNoDisponible):
        AnalizadorNoDisponible().analizar("video.mp4")
