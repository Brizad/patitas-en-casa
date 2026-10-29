"""Rutas del video (#125): subida del ciudadano, trabajador local y vista del personal."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"  # falso
CLAVE = "clave-de-prueba-larga"  # falsa
TOKEN = "token-de-trabajador-falso-para-pruebas"  # falso
LLAVE = "clave-del-telefono-0001"
REPORTE = {"descripcion": "Perro cojeando en el parque, no apoya una pata",
           "direccion": "Calle 10 # 5-20"}
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 2000


@pytest.fixture
def c(tmp_path):
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana", Rol.VETERINARIO, CLAVE)
    app = crear_app(RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
                    repositorio_usuarios=usuarios, emisor_tokens=EmisorTokens(SECRETO),
                    token_video=TOKEN, directorio_videos=str(tmp_path))
    cliente = TestClient(app)
    cliente.directorio = tmp_path
    return cliente


def sesion(c):
    token = c.post("/auth/token", data={"username": "vet@patitas.co", "password": CLAVE})
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def reportar(c):
    return c.post("/reportes", json=REPORTE, headers={"Idempotency-Key": LLAVE}).json()["codigo"]


def subir(c, codigo, datos=MP4, llave=LLAVE):
    return c.post(f"/reportes/{codigo}/video", content=datos,
                  headers={"Idempotency-Key": llave, "Content-Type": "video/mp4"})


def test_el_ciudadano_sube_el_video_y_queda_pendiente(c):
    r = subir(c, reportar(c))
    assert r.status_code == 202
    assert r.json()["mensaje"] == "Video recibido, se está analizando."


def test_solo_el_telefono_que_creo_el_reporte_sube_el_video(c):
    codigo = reportar(c)
    assert subir(c, codigo, llave="otra-llave-cualquiera-1").status_code == 403
    assert c.post(f"/reportes/{codigo}/video", content=MP4).status_code == 403
    assert subir(c, codigo, datos=b"no soy un video" * 10).status_code == 415
    assert subir(c, codigo).status_code == 202
    assert subir(c, codigo).status_code == 409


def test_el_personal_ve_el_estado_del_video_con_sesion(c):
    codigo = reportar(c)
    subir(c, codigo)
    vista = c.get(f"/reportes/{codigo}/video", headers=sesion(c)).json()
    assert (vista["estado"], vista["tiene_tira"]) == ("pendiente", False)
    assert len(list(c.directorio.iterdir())) == 1  # espera en el disco temporal
    assert c.get(f"/reportes/{codigo}/video/tira.png", headers=sesion(c)).status_code == 404
    assert c.get(f"/reportes/{codigo}/video").status_code == 401
    assert c.get(f"/reportes/{codigo}/video/tira.png").status_code == 401


def test_sin_token_configurado_el_video_esta_apagado_y_manda_el_texto(tmp_path):
    app = crear_app(RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
                    repositorio_usuarios=RepositorioUsuariosEnMemoria(),
                    emisor_tokens=EmisorTokens(SECRETO), directorio_videos=str(tmp_path))
    c = TestClient(app)
    codigo = reportar(c)
    r = subir(c, codigo)
    assert r.status_code == 503
    assert "se atiende con la descripción" in r.json()["detail"]
