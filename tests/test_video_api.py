"""Rutas del video (#125): subida del ciudadano, trabajador local y vista del personal."""
import base64

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
TIRA = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50).decode()
RESULTADO = {"prioridad": "critica", "confianza": 0.9, "version_modelo": "marcha-mlp-v1",
             "evidencias": ["no se pone de pie en el video", "apoya las cuatro patas",
                            "casi no se desplaza"], "medidas": {"de_pie": 0.0},
             "tira_png_base64": TIRA}
TRABAJADOR = {"X-Video-Token": TOKEN}


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
    assert c.post("/video/trabajos/reclamar", headers=TRABAJADOR).status_code == 503


def test_recorrido_completo_del_video(c):
    codigo = reportar(c)
    r = subir(c, codigo)
    assert r.status_code == 202
    assert r.json()["mensaje"] == "Video recibido, se está analizando."
    trabajo = c.post("/video/trabajos/reclamar", headers=TRABAJADOR).json()
    assert trabajo["codigo"] == codigo
    assert c.post("/video/trabajos/reclamar", headers=TRABAJADOR).status_code == 204
    assert c.get(f"/video/trabajos/{trabajo['id']}/archivo", headers=TRABAJADOR).content == MP4
    hecho = c.post(f"/video/trabajos/{trabajo['id']}/resultado", json=RESULTADO,
                   headers=TRABAJADOR)
    assert hecho.json() == {"estado": "terminado", "discrepancia": True}
    assert list(c.directorio.iterdir()) == []  # RNF-08: el video se borró
    vet = sesion(c)
    vista = c.get(f"/reportes/{codigo}/video", headers=vet).json()
    assert (vista["estado"], vista["prioridad"], vista["tiene_tira"]) == (
        "terminado", "critica", True)
    assert c.get(f"/reportes/{codigo}/video/tira.png", headers=vet).content.startswith(b"\x89PNG")
    cola = c.get("/cola", headers=vet).json()
    assert cola[0]["prioridad"] == "critica"  # RN-07: ganó el video, más grave
    # RN-14: la consulta pública no muestra nada del video.
    assert "video" not in str(c.get(f"/reportes/{codigo}/seguimiento").json())


def test_el_trabajador_necesita_su_token_y_el_personal_su_sesion(c):
    codigo = reportar(c)
    assert c.post("/video/trabajos/reclamar").status_code == 401
    assert c.post("/video/trabajos/reclamar",
                  headers={"X-Video-Token": "otro-token"}).status_code == 401
    assert c.get(f"/reportes/{codigo}/video").status_code == 401
    assert c.get(f"/reportes/{codigo}/video/tira.png").status_code == 401


def test_un_resultado_con_prioridad_necesita_tres_evidencias(c):
    subir(c, reportar(c))
    id_ = c.post("/video/trabajos/reclamar", headers=TRABAJADOR).json()["id"]
    corto = {**RESULTADO, "evidencias": ["no se pone de pie"]}
    assert c.post(f"/video/trabajos/{id_}/resultado", json=corto,
                  headers=TRABAJADOR).status_code == 422
    malo = {**RESULTADO, "tira_png_base64": base64.b64encode(b"GIF89a").decode()}
    assert c.post(f"/video/trabajos/{id_}/resultado", json=malo,
                  headers=TRABAJADOR).status_code == 422
    fallo = c.post(f"/video/trabajos/{id_}/fallo", json={"motivo": "sin memoria"},
                   headers=TRABAJADOR)
    assert fallo.json() == {"estado": "pendiente"}  # se reintenta


def test_la_bitacora_registra_al_trabajador_pero_no_cada_sondeo_vacio(c):
    subir(c, reportar(c))
    id_ = c.post("/video/trabajos/reclamar", headers=TRABAJADOR).json()["id"]
    c.post("/video/trabajos/reclamar", headers=TRABAJADOR)  # 204: sin trabajos
    c.post(f"/video/trabajos/{id_}/resultado", json=RESULTADO, headers=TRABAJADOR)
    acciones = [(e.actor, e.accion) for e in c.app.state.bitacora.recientes()]
    assert ("trabajador de video", "POST /video/trabajos/{id_}/resultado") in acciones
    assert acciones.count(("trabajador de video", "POST /video/trabajos/reclamar")) == 1
