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
    assert r.evidencias[:2] == ["señal 'cojea' -> media",
                                "video: no apoya la pata trasera izquierda"]
    assert "discrepancia: texto media, video alta" in r.evidencias[2]  # RF-19
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


# --- Parte 7a: RN-02 también cuando el video sube la prioridad ---

def test_rn02_el_video_que_sube_a_media_con_poca_confianza_pide_revision():
    """Antes: aplicar_video dejaba «clasificado» sin mirar la confianza. Un reporte baja que el
    video sube a media con 0,55 de confianza tendría una prioridad media automática con baja
    confianza, justo lo que RN-02 prohíbe."""
    r = Reporte(codigo="ABCD1234", descripcion="Perrito durmiendo en el andén del barrio",
                ubicacion=Ubicacion(direccion="Calle 10"), prioridad=Prioridad.BAJA,
                confianza=0.9, evidencias=[], estado=EstadoReporte.CLASIFICADO)
    assert aplicar_video(r, Resultado(Prioridad.MEDIA, 0.55, ["cojea un poco"])) is True
    assert (r.prioridad, r.estado) == (Prioridad.MEDIA, EstadoReporte.REQUIERE_REVISION)


def test_rn02_alta_o_critica_no_se_degradan_aunque_la_confianza_sea_baja():
    r = reporte()
    assert aplicar_video(r, Resultado(Prioridad.CRITICA, 0.4, ["no se mueve"])) is True
    assert (r.prioridad, r.estado) == (Prioridad.CRITICA, EstadoReporte.CLASIFICADO)


def test_rn02_media_con_buena_confianza_queda_clasificada():
    r = Reporte(codigo="ABCD1234", descripcion="Perrito durmiendo en el andén del barrio",
                ubicacion=Ubicacion(direccion="Calle 10"), prioridad=Prioridad.BAJA,
                confianza=0.9, evidencias=[], estado=EstadoReporte.CLASIFICADO)
    assert aplicar_video(r, Resultado(Prioridad.MEDIA, 0.8, [])) is True
    assert r.estado == EstadoReporte.CLASIFICADO
