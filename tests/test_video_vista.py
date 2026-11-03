"""Vista previa del video para el veterinario (#214, cambia RNF-08)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import EstadoReporte, Prioridad, Refugio, Reporte, Rol, Ubicacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios
from app.video.repositorio import RepositorioVideosEnMemoria
from app.video.servicio import ServicioVideo, VideoRechazado
from tests.test_video_api import CLAVE as CLAVE_VET
from tests.test_video_api import (
    LLAVE,
    RESULTADO,
    SECRETO,
    TOKEN,
    TRABAJADOR,
    reportar,
    sesion,
    subir,
)
from tests.test_video_trabajos import CLAVE, INICIO, VIDEO_ALTA, AlmacenFalso, Reloj

VISTA = b"\x00\x00\x00\x18ftypisom" + b"\x05" * 3000


@pytest.fixture
def c(tmp_path):
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana", Rol.VETERINARIO, CLAVE_VET)
    app = crear_app(RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
                    repositorio_usuarios=usuarios, emisor_tokens=EmisorTokens(SECRETO),
                    token_video=TOKEN, directorio_videos=str(tmp_path))
    return TestClient(app)


def subir_vista(c, id_, datos=VISTA, encabezados=TRABAJADOR):
    return c.post(f"/video/trabajos/{id_}/vista", content=datos, headers=encabezados)


def reclamado(c):
    codigo = reportar(c)
    assert subir(c, codigo).status_code == 202
    return codigo, c.post("/video/trabajos/reclamar", headers=TRABAJADOR).json()["id"]


def test_el_trabajador_sube_la_vista_y_el_veterinario_la_ve(c):
    codigo, id_ = reclamado(c)
    assert subir_vista(c, id_).status_code == 200
    c.post(f"/video/trabajos/{id_}/resultado", json=RESULTADO, headers=TRABAJADOR)
    r = c.get(f"/reportes/{codigo}/video/vista.mp4", headers=sesion(c))
    assert r.status_code == 200 and r.content == VISTA
    assert r.headers["content-type"] == "video/mp4"
    assert r.headers["cache-control"] == "private, no-store"
    assert c.get(f"/reportes/{codigo}/video", headers=sesion(c)).json()["tiene_vista"] is True


def test_la_vista_exige_sesion_del_personal_y_el_token_del_trabajador(c):
    codigo, id_ = reclamado(c)
    assert subir_vista(c, id_, encabezados={}).status_code == 401
    assert subir_vista(c, id_, encabezados={"X-Video-Token": "otro"}).status_code == 401
    subir_vista(c, id_)
    assert c.get(f"/reportes/{codigo}/video/vista.mp4").status_code == 401  # sin sesión
    assert c.get(f"/reportes/{codigo}/video/vista.mp4",
                 headers={"Idempotency-Key": LLAVE}).status_code == 401  # ni con la clave


def test_sin_vista_responde_404_y_lo_dice_el_estado(c):
    codigo, id_ = reclamado(c)
    c.post(f"/video/trabajos/{id_}/resultado", json=RESULTADO, headers=TRABAJADOR)
    assert c.get(f"/reportes/{codigo}/video/vista.mp4", headers=sesion(c)).status_code == 404
    assert c.get(f"/reportes/{codigo}/video", headers=sesion(c)).json()["tiene_vista"] is False


def test_la_vista_debe_ser_un_mp4_de_cinco_megas_o_menos(c):
    _, id_ = reclamado(c)
    assert subir_vista(c, id_, b"no soy un video" * 10).status_code == 415
    grande = VISTA + b"\x00" * (5 * 1024 * 1024)
    assert subir_vista(c, id_, grande).status_code == 413


def test_la_vista_solo_se_sube_a_un_trabajo_en_analisis(c):
    assert subir_vista(c, 999).status_code == 404
    _, id_ = reclamado(c)
    c.post(f"/video/trabajos/{id_}/resultado", json=RESULTADO, headers=TRABAJADOR)
    assert subir_vista(c, id_).status_code == 409


def test_el_video_original_se_borra_y_solo_queda_la_vista(c, tmp_path):
    _, id_ = reclamado(c)
    subir_vista(c, id_)
    c.post(f"/video/trabajos/{id_}/resultado", json=RESULTADO, headers=TRABAJADOR)
    restantes = [p.suffix for p in tmp_path.iterdir()]
    assert restantes == [".vista"]  # RNF-08: el original no se guarda; la vista sí, 7 días


def test_una_segunda_vista_reemplaza_a_la_primera(c, tmp_path):
    _, id_ = reclamado(c)
    subir_vista(c, id_)
    nueva = VISTA + b"\x09" * 10
    subir_vista(c, id_, nueva)
    assert [p.read_bytes() for p in tmp_path.glob("*.vista")] == [nueva]


# --- Borrado: a los 7 días o al cerrarse el reporte ---

@pytest.fixture
def entorno():
    reportes, reloj = RepositorioEnMemoria(), Reloj()
    almacen, vistas = AlmacenFalso(), AlmacenFalso()
    reportes.guardar_con_clave(Reporte(
        "ABCD1234", "Perro cojeando cerca del parque", Ubicacion(direccion="Calle 10"),
        estado=EstadoReporte.CONFIRMADO, prioridad=Prioridad.ALTA, confianza=0.9,
        evidencias=["cojea"], creado_en=INICIO), CLAVE)
    atendidos = set()
    servicio = ServicioVideo(RepositorioVideosEnMemoria(), reportes, almacen, reloj,
                             almacen_vistas=vistas, rescate_atendido=atendidos.__contains__)
    servicio.autorizar_subida("ABCD1234", CLAVE)
    almacen.archivos.add("v.mp4")
    trabajo = servicio.registrar("ABCD1234", "v.mp4", 100)
    servicio.reclamar()
    vistas.archivos.add("vista1")
    servicio.registrar_vista(trabajo.id, "vista1", 3000)
    return servicio, reportes, vistas, reloj, atendidos


def test_la_vista_se_conserva_mientras_el_reporte_siga_abierto(entorno):
    servicio, _, vistas, reloj, _ = entorno
    reloj.ahora += timedelta(days=config.VISTA_VIDEO_DIAS) - timedelta(minutes=1)
    servicio.revisar()
    assert "vista1" in vistas.archivos
    assert servicio.vista_de("ABCD1234") == ("vista1", 3000)


def test_la_vista_se_borra_a_los_7_dias(entorno):
    servicio, _, vistas, reloj, _ = entorno
    assert config.VISTA_VIDEO_DIAS == 7
    reloj.ahora += timedelta(days=7, minutes=1)
    servicio.revisar()
    assert "vista1" not in vistas.archivos
    assert servicio.vista_de("ABCD1234") is None


def test_la_vista_se_borra_al_descartar_el_reporte(entorno):
    servicio, reportes, vistas, _, _ = entorno
    reporte = reportes.buscar("ABCD1234")
    reporte.estado = EstadoReporte.DESCARTADO
    reportes.actualizar_triaje(reporte)
    servicio.revisar()
    assert "vista1" not in vistas.archivos


def test_la_vista_se_borra_al_terminar_el_rescate(entorno):
    servicio, _, vistas, _, atendidos = entorno
    servicio.revisar()
    assert "vista1" in vistas.archivos  # el rescate sigue en curso
    atendidos.add("ABCD1234")
    servicio.revisar()
    assert "vista1" not in vistas.archivos


def test_registrar_una_vista_en_un_trabajo_cerrado_la_descarta(entorno):
    servicio, _, vistas, _, _ = entorno
    servicio.terminar(1, VIDEO_ALTA)
    vistas.archivos.add("tarde")
    with pytest.raises(VideoRechazado) as error:
        servicio.registrar_vista(1, "tarde", 10)
    assert error.value.estado_http == 409 and "tarde" not in vistas.archivos
