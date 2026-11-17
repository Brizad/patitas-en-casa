"""#231: la API sabe si el nodo de video está encendido, qué versión corre y por qué un
análisis llegó sin vista previa. Antes nadie podía saberlo sin mirar la ventana de Ubuntu."""
from datetime import timedelta

import httpx
import patitas_video
import pytest
from fastapi.testclient import TestClient
from patitas_video.trabajador import procesar_uno

from app import config
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios
from app.video.repositorio import RepositorioVideosEnMemoria
from app.video.servicio import ServicioVideo, version_al_dia
from tests.test_video_api import CLAVE, SECRETO, TOKEN, TRABAJADOR, reportar, sesion, subir
from tests.test_video_trabajador import RESULTADO_CON_VISTA, ApiFalsa, cliente
from tests.test_video_trabajos import AlmacenFalso, Reloj

NODO = {**TRABAJADOR, "X-Video-Nodo": patitas_video.__version__}


@pytest.fixture
def c(tmp_path):
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana", Rol.VETERINARIO, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios, emisor_tokens=EmisorTokens(SECRETO),
        token_video=TOKEN, directorio_videos=str(tmp_path)))


def test_el_estado_del_nodo_exige_sesion_del_personal(c):
    assert c.get("/video/nodo").status_code == 401


def test_sin_contacto_el_nodo_figura_apagado(c):
    estado = c.get("/video/nodo", headers=sesion(c)).json()
    assert estado == {"activado": True, "version_minima": config.VERSION_MINIMA_NODO_VIDEO,
                      "ultimo_contacto": None, "segundos_sin_contacto": None, "version": None,
                      "analizando": False, "en_linea": False, "al_dia": None}


def test_cada_consulta_del_nodo_deja_su_contacto_y_su_version(c):
    assert c.post("/video/trabajos/reclamar", headers=NODO).status_code == 204
    estado = c.get("/video/nodo", headers=sesion(c)).json()
    assert estado["en_linea"] and estado["al_dia"]
    assert estado["version"] == patitas_video.__version__
    assert estado["ultimo_contacto"].endswith("+00:00") and estado["segundos_sin_contacto"] < 5


def test_un_nodo_viejo_que_no_dice_su_version_no_esta_al_dia(c):
    c.post("/video/trabajos/reclamar", headers=TRABAJADOR)
    estado = c.get("/video/nodo", headers=sesion(c)).json()
    assert estado["en_linea"] and estado["version"] is None and estado["al_dia"] is False


def test_un_token_malo_no_cuenta_como_contacto(c):
    c.post("/video/trabajos/reclamar", headers={"X-Video-Token": "otro", "X-Video-Nodo": "9.9"})
    assert c.get("/video/nodo", headers=sesion(c)).json()["ultimo_contacto"] is None


def test_la_version_minima_es_la_del_nodo_de_este_repositorio():
    assert version_al_dia(patitas_video.__version__)
    assert not version_al_dia("1.2.9") and not version_al_dia(None)
    assert not version_al_dia("no-es-una-version")


def _servicio():
    reloj = Reloj()
    return ServicioVideo(RepositorioVideosEnMemoria(), RepositorioEnMemoria(), AlmacenFalso(),
                         reloj), reloj


def test_sin_consultas_un_rato_el_nodo_deja_de_estar_en_linea():
    servicio, reloj = _servicio()
    servicio.latido("1.3.0")
    reloj.ahora += timedelta(seconds=config.NODO_VIDEO_EN_LINEA_S)
    assert servicio.estado_nodo()["en_linea"]
    reloj.ahora += timedelta(seconds=1)
    estado = servicio.estado_nodo()
    assert not estado["en_linea"] and estado["segundos_sin_contacto"] == (
        config.NODO_VIDEO_EN_LINEA_S + 1)


def test_mientras_analiza_el_nodo_no_consulta_pero_sigue_en_linea(c):
    """Un análisis tarda minutos y en ese rato el nodo no llama a la API: no es estar apagado."""
    assert subir(c, reportar(c)).status_code == 202
    assert c.post("/video/trabajos/reclamar", headers=NODO).status_code == 200
    assert c.get("/video/nodo", headers=sesion(c)).json()["analizando"] is True


def test_el_nodo_ocupado_vuelve_a_libre_al_entregar_o_al_vencer_el_reclamo():
    servicio, reloj = _servicio()
    servicio.latido("1.3.0", ocupado=True)
    reloj.ahora += timedelta(seconds=config.VENCIMIENTO_RECLAMO_VIDEO_S - 1)
    assert servicio.estado_nodo()["en_linea"]
    reloj.ahora += timedelta(seconds=2)
    assert not servicio.estado_nodo()["en_linea"]  # se apagó a mitad del análisis
    servicio.latido("1.3.0", ocupado=True)
    servicio.latido("1.3.0", ocupado=False)
    assert not servicio.estado_nodo()["analizando"]


# --- El nodo: dice su versión y por qué no hubo vista ---

def test_el_nodo_envia_su_version_en_cada_peticion():
    vistas = []

    def api(peticion: httpx.Request) -> httpx.Response:
        vistas.append(peticion.headers.get("x-video-nodo"))
        return httpx.Response(204)
    cliente(api).reclamar()
    assert vistas == [patitas_video.__version__]


def test_si_no_hubo_vista_el_motivo_viaja_en_las_medidas():
    api = ApiFalsa()
    procesar_uno(cliente(api), lambda _r: {
        "prioridad": None, "confianza": 0.0, "evidencias": [],
        "sin_vista": "ffmpeg no está instalado (sudo apt install ffmpeg)"})
    assert api.entregados[0]["medidas"]["sin_vista"].startswith("ffmpeg no está instalado")


def test_si_la_api_rechaza_la_vista_el_motivo_viaja_en_las_medidas():
    api = ApiFalsa(vista_estado=413)
    procesar_uno(cliente(api), lambda _r: dict(RESULTADO_CON_VISTA))
    assert "413" in api.entregados[0]["medidas"]["sin_vista"]


def test_con_vista_subida_no_hay_motivo_y_las_medidas_dicen_la_version_del_nodo():
    api = ApiFalsa()
    procesar_uno(cliente(api), lambda _r: dict(RESULTADO_CON_VISTA))
    medidas = api.entregados[0]["medidas"]
    assert "sin_vista" not in medidas and medidas["version_nodo"] == patitas_video.__version__

