"""Trabajador local (#125): contrato con la API de Render, con un servidor falso."""
import os

import httpx
import pytest
from patitas_video.cliente import ApiNoDisponible, ClienteApi
from patitas_video.trabajador import ESPERA_SIN_TRABAJO_S, procesar_uno, trabajar

TOKEN = "token-de-trabajador-falso-para-pruebas"  # falso
VIDEO = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100


class ApiFalsa:
    """Imita las rutas del trabajador en Render y anota lo que recibe."""

    def __init__(self, trabajos=1, caida=False, lenta=False, sin_vista=False, vista_estado=200):
        self.trabajos, self.caida, self.lenta = trabajos, caida, lenta
        self.sin_vista = sin_vista  # una API anterior que no conoce la ruta de la vista
        self.vista_estado = vista_estado  # #231: la API (o un proxy) rechaza la vista
        self.entregados, self.fallos, self.vistas = [], [], []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        if self.lenta:
            raise httpx.ReadTimeout("Render está despertando", request=peticion)
        if self.caida:
            return httpx.Response(502)
        if peticion.headers.get("x-video-token") != TOKEN:
            return httpx.Response(401, json={"detail": "token"})
        ruta = peticion.url.path
        if ruta.endswith("/reclamar"):
            if not self.trabajos:
                return httpx.Response(204)
            self.trabajos -= 1
            return httpx.Response(200, json={"id": 7, "codigo": "ABCD1234", "bytes": 116})
        if ruta.endswith("/archivo"):
            return httpx.Response(200, content=VIDEO)
        if ruta.endswith("/vista"):
            if self.sin_vista:
                return httpx.Response(404, json={"detail": "no existe"})
            if self.vista_estado != 200:
                return httpx.Response(self.vista_estado, json={"detail": "rechazada"})
            self.vistas.append((peticion.headers.get("content-type"), peticion.content))
            return httpx.Response(200, json={"bytes": len(peticion.content)})
        cuerpo = httpx.Response(200, content=peticion.content).json()
        (self.entregados if ruta.endswith("/resultado") else self.fallos).append(cuerpo)
        return httpx.Response(200, json={"estado": "terminado"})


def cliente(api, token=TOKEN):
    return ClienteApi("https://api.falsa", token, httpx.Client(transport=httpx.MockTransport(api)))


def test_reclama_descarga_analiza_entrega_y_borra_el_video():
    api, vistos = ApiFalsa(), []

    def analizar_falso(ruta):
        with open(ruta, "rb") as archivo:
            vistos.append((ruta, archivo.read()))
        return {"prioridad": "alta", "confianza": 0.8, "evidencias": ["a", "b", "c"],
                "tira": b"\x89PNG"}

    assert procesar_uno(cliente(api), analizar_falso) is True
    assert vistos[0][1] == VIDEO
    assert api.entregados[0]["tira_png_base64"] == "iVBORw=="
    assert not os.path.exists(vistos[0][0])  # RNF-08: el video local se borró
    assert procesar_uno(cliente(api), analizar_falso) is False  # 204: no hay más


def test_si_el_analisis_falla_se_informa_para_reintentar():
    api = ApiFalsa()

    def roto(_ruta):
        raise MemoryError("sin memoria")

    procesar_uno(cliente(api), roto)
    assert api.fallos == [{"motivo": "MemoryError: sin memoria"}]


def test_token_malo_detiene_el_trabajador_con_un_mensaje_claro():
    with pytest.raises(PermissionError, match="PATITAS_VIDEO_TOKEN"):
        cliente(ApiFalsa(), token="otro").reclamar()


@pytest.mark.parametrize("api", [ApiFalsa(caida=True), ApiFalsa(lenta=True)])
def test_api_caida_o_lenta_espera_cada_vez_mas(api):
    with pytest.raises(ApiNoDisponible):
        cliente(api).reclamar()
    esperas = []

    class Basta(Exception):
        pass

    def dormir(segundos):
        esperas.append(segundos)
        if len(esperas) == 3:
            raise Basta

    with pytest.raises(Basta):
        trabajar(cliente(api), lambda _r: {}, dormir=dormir)
    assert esperas == [ESPERA_SIN_TRABAJO_S * 2, ESPERA_SIN_TRABAJO_S * 4,
                       ESPERA_SIN_TRABAJO_S * 8]


RESULTADO_CON_VISTA = {"prioridad": "alta", "confianza": 0.8, "evidencias": ["a", "b", "c"],
                       "vista": b"0000ftyp-mp4-falso"}


def test_la_vista_previa_se_sube_y_no_viaja_en_el_json_del_resultado():
    api = ApiFalsa()
    procesar_uno(cliente(api), lambda _r: dict(RESULTADO_CON_VISTA))
    assert api.vistas == [("video/mp4", b"0000ftyp-mp4-falso")]
    assert "vista" not in api.entregados[0]


def test_si_la_api_no_acepta_la_vista_el_resultado_se_entrega_igual():
    api = ApiFalsa(sin_vista=True)
    procesar_uno(cliente(api), lambda _r: dict(RESULTADO_CON_VISTA))
    assert len(api.entregados) == 1


@pytest.mark.parametrize("estado", [400, 403, 413, 415, 422])
def test_regresion_231_un_rechazo_de_la_vista_no_tumba_al_nodo(estado, caplog):
    api = ApiFalsa(vista_estado=estado)
    procesar_uno(cliente(api), lambda _r: dict(RESULTADO_CON_VISTA))
    assert len(api.entregados) == 1  # el resultado llega igual
    assert "vista previa del trabajo 7 no subida" in caplog.text


def test_regresion_231_el_log_dice_que_la_vista_se_subio_y_su_tamano(caplog):
    caplog.set_level("INFO", logger="patitas_video")
    procesar_uno(cliente(ApiFalsa()), lambda _r: dict(RESULTADO_CON_VISTA))
    assert "vista previa del trabajo 7 subida" in caplog.text


def test_regresion_231_sin_vista_el_log_dice_por_que_y_no_viaja_a_la_api(caplog):
    api = ApiFalsa()
    resultado = {"prioridad": None, "confianza": 0.0, "evidencias": [],
                 "sin_vista": "ffmpeg no está instalado"}
    procesar_uno(cliente(api), lambda _r: dict(resultado))
    assert "trabajo 7 sin vista previa: ffmpeg no está instalado" in caplog.text
    assert "sin_vista" not in api.entregados[0] and api.vistas == []
