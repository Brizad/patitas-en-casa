"""Robustez del nodo de video (#231): Render se reinicia en cada despliegue, la API puede
rechazar un resultado y el PC puede ser lento. Nada de eso debe tumbar al nodo ni tirar a la
basura un análisis que ya costó minutos."""
import httpx
import pytest
from patitas_video.analisis import MAX_SEGUNDOS_ANALISIS, analizar
from patitas_video.clasificador import ClasificadorMarcha
from patitas_video.cliente import ApiNoDisponible
from patitas_video.trabajador import ESPERAS_ENTREGA_S, procesar_uno, trabajar

from tests.test_video_analisis import Detector, Estimador, Lector
from tests.test_video_trabajador import RESULTADO_CON_VISTA, ApiFalsa, cliente
from tests.trayectorias_video import caminar

RESULTADO = {"prioridad": "alta", "confianza": 0.8, "evidencias": ["a", "b", "c"]}


def con_respuesta(api, final_de_ruta, estado, veces=10**6):
    """La API falsa, pero las primeras «veces» peticiones a esa ruta responden «estado»."""
    cuenta = {"n": 0}

    def manejar(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path.endswith(final_de_ruta) and cuenta["n"] < veces:
            cuenta["n"] += 1
            return httpx.Response(estado, json={"detail": "motivo de la API"})
        return api(peticion)
    return manejar


def test_un_502_al_entregar_se_reintenta_sin_volver_a_analizar():
    api, analisis, esperas = ApiFalsa(), [], []

    def analizar_falso(ruta):
        analisis.append(ruta)
        return dict(RESULTADO)
    hubo = procesar_uno(cliente(con_respuesta(api, "/resultado", 502, veces=2)), analizar_falso,
                        dormir=esperas.append)
    assert hubo and len(analisis) == 1 and len(api.entregados) == 1
    assert esperas == list(ESPERAS_ENTREGA_S[:2])


def test_si_render_no_vuelve_el_trabajo_queda_para_reclamarlo_despues():
    api, esperas = ApiFalsa(), []
    with pytest.raises(ApiNoDisponible):
        procesar_uno(cliente(con_respuesta(api, "/resultado", 502)), lambda _r: dict(RESULTADO),
                     dormir=esperas.append)
    assert esperas == list(ESPERAS_ENTREGA_S) and api.entregados == []


def test_un_resultado_rechazado_no_tumba_al_nodo_y_queda_como_fallo():
    api = ApiFalsa()
    hubo = procesar_uno(cliente(con_respuesta(api, "/resultado", 422)), lambda _r: dict(RESULTADO))
    assert hubo and api.entregados == []
    assert "422" in api.fallos[0]["motivo"] and "motivo de la API" in api.fallos[0]["motivo"]


def test_si_informar_el_fallo_tambien_falla_el_nodo_sigue(caplog):
    def roto(_ruta):
        raise MemoryError("sin memoria")
    api = ApiFalsa()
    assert procesar_uno(cliente(con_respuesta(api, "/fallo", 409)), roto) is True
    assert "no se pudo informar el fallo del trabajo 7" in caplog.text


def test_la_vista_tambien_se_reintenta_si_render_se_esta_reiniciando():
    api, esperas = ApiFalsa(), []
    procesar_uno(cliente(con_respuesta(api, "/vista", 502, veces=1)),
                 lambda _r: dict(RESULTADO_CON_VISTA), dormir=esperas.append)
    assert len(api.vistas) == 1 and "sin_vista" not in api.entregados[0]["medidas"]
    assert esperas == [ESPERAS_ENTREGA_S[0]]


class Basta(Exception):
    pass


def _dormir_dos_veces():
    esperas = []

    def dormir(segundos):
        esperas.append(segundos)
        if len(esperas) == 2:
            raise Basta
    return dormir


def test_un_error_inesperado_no_detiene_el_ciclo(caplog):
    api = con_respuesta(ApiFalsa(), "/reclamar", 400)  # algo que el nodo no esperaba
    with pytest.raises(Basta):  # siguió dando vueltas hasta que la prueba lo detuvo
        trabajar(cliente(api), lambda _r: {}, dormir=_dormir_dos_veces())
    assert "el nodo sigue" in caplog.text


def test_el_token_malo_si_detiene_al_nodo():
    with pytest.raises(PermissionError, match="PATITAS_VIDEO_TOKEN"):
        trabajar(cliente(ApiFalsa(), token="otro"), lambda _r: {}, dormir=_dormir_dos_veces())


def test_un_equipo_lento_corta_el_analisis_antes_de_que_venza_el_reclamo():
    """El reclamo vence a los 10 min: pasado el tope el resultado es «no concluyente» (manda el
    texto) en vez de seguir analizando un trabajo que la API ya dio por perdido."""
    reloj = iter(range(0, 10**6, 60))  # cada cuadro «tarda» un minuto
    resultado = analizar("video.mp4", Lector(caminar(8.0)), Detector(), Estimador(),
                         ClasificadorMarcha.desde_json(), reloj=lambda: next(reloj))
    assert resultado["prioridad"] is None
    assert "tardó más de" in resultado["motivo"] and MAX_SEGUNDOS_ANALISIS == 480
