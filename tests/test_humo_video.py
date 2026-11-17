"""La prueba de humo del video (#231) contra la API real en memoria y el ciclo real del nodo
(`procesar_uno`); solo el análisis pesado (MediaPipe, DeepLabCut, ffmpeg) es de mentira. Es el
mismo recorrido que hace `video-humo.yml` con los modelos de verdad."""
import pytest
from fastapi.testclient import TestClient
from patitas_video.cliente import ClienteApi
from patitas_video.trabajador import procesar_uno

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios
from scripts.operacion.humo_video import HumoFallido, humo
from tests.test_video_api import CLAVE, MP4, SECRETO, TOKEN

VISTA = b"\x00\x00\x00\x18ftypisom" + b"\x07" * 4000
NO_CONCLUYENTE = {"prioridad": None, "confianza": 0.0, "evidencias": [],
                  "motivo": "no se ve un perro o un gato en la mayor parte del video"}


@pytest.fixture
def api(tmp_path):
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana", Rol.VETERINARIO, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios, emisor_tokens=EmisorTokens(SECRETO),
        token_video=TOKEN, directorio_videos=str(tmp_path)))


def nodo(api, resultado):
    """El trabajador de verdad hablando con esta API; el análisis devuelve «resultado»."""
    cliente = ClienteApi("http://testserver", TOKEN, http=api)
    return lambda: procesar_uno(cliente, lambda _ruta: dict(resultado))


def test_el_recorrido_completo_llega_hasta_la_vista_que_ve_el_veterinario(api):
    """El caso que se vio en producción: análisis «no concluyente», y aun así con vista."""
    pasos = []
    con_vista = nodo(api, {**NO_CONCLUYENTE, "vista": VISTA})
    analisis = humo(api, MP4, "vet@patitas.co", CLAVE, con_vista, pasos.append)
    assert analisis["estado"] == "no_concluyente" and analisis["tiene_vista"] is True
    assert len(pasos) == 4 and "al día" in pasos[-1]


def test_si_el_nodo_no_genera_la_vista_el_humo_falla_y_dice_por_que(api):
    sin_ffmpeg = {**NO_CONCLUYENTE, "sin_vista": "ffmpeg no está instalado"}
    with pytest.raises(HumoFallido, match="SIN vista previa: ffmpeg no está instalado"):
        humo(api, MP4, "vet@patitas.co", CLAVE, nodo(api, sin_ffmpeg), lambda _m: None)


def test_si_la_vista_no_es_un_mp4_la_api_la_rechaza_y_el_humo_lo_dice(api):
    with pytest.raises(HumoFallido, match="SIN vista previa: la API no aceptó la vista"):
        humo(api, MP4, "vet@patitas.co", CLAVE,
             nodo(api, {**NO_CONCLUYENTE, "vista": b"esto no es un video" * 10}), lambda _m: None)


def test_si_el_nodo_esta_apagado_el_humo_falla(api):
    with pytest.raises(HumoFallido, match="quedó «pendiente»"):
        humo(api, MP4, "vet@patitas.co", CLAVE, lambda: None, lambda _m: None)
