"""#504: llegada al sitio, informe de rescate con fotos de evidencia y foto del reporte."""
import json

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
ANA, LUIS = "ana@rescate.co", "luis@rescate.co"
VET, COORD = "vet@patitas.co", "coord@patitas.co"
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 2000  # basta con la firma: el servidor mira los bytes
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 500
NOTA = "Tenía una pata lastimada; se dejó cargar sin problema."


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    servicio = ServicioUsuarios(usuarios)
    for correo, nombre, rol in [
            (VET, "Dra. Vet", Rol.VETERINARIO), (COORD, "Coord", Rol.COORDINADOR),
            (ANA, "Ana Ruiz", Rol.RESCATISTA), (LUIS, "Luis", Rol.RESCATISTA),
            ("adop@correo.co", "Adoptante", Rol.ADOPTANTE)]:
        servicio.registrar(correo, nombre, rol, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def en_el_sitio(c, llegar=True, clave="clave-del-reporte-0001"):
    codigo = c.post("/reportes", headers={"Idempotency-Key": clave}, json={
        "descripcion": "Perro atropellado en la avenida, está sangrando mucho",
        "latitud": 7.8939, "longitud": -72.5078}).json()["codigo"]
    c.post(f"/reportes/{codigo}/confirmacion", headers=sesion(c, VET),
           json={"prioridad": "critica", "justificacion": "Sangra mucho y no se mueve"})
    ana = sesion(c, ANA)
    c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=ana)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    if llegar:
        assert c.post(f"/rescates/{codigo}/llegue", headers=ana).status_code == 200
    return codigo, ana


def informe(c, codigo, cabeceras, fotos=(JPEG,), **campos):
    datos = {"encontrado": "si", "estados": ["herido", "asustado_agresivo"],
             "accion": "trasladado", "nota": NOTA, **campos}
    archivos = [("fotos", (f"f{i}.jpg", f, "image/jpeg")) for i, f in enumerate(fotos)]
    return c.post(f"/rescates/{codigo}/informe", data=datos, files=archivos or None,
                  headers=cabeceras)


def test_informe_completo_pasa_a_atendido_y_queda_en_el_historial(c):
    codigo, ana = en_el_sitio(c)
    respuesta = informe(c, codigo, ana, fotos=(JPEG, PNG))
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert (datos["resultado"], datos["rescatista"]) == ("trasladado", "Ana Ruiz")
    assert len(datos["fotos"]) == 2
    assert datos["estados"] == ["herido", "asustado_agresivo"] and datos["creado_en"]
    assert c.get("/rescates/historial", headers=ana).json()[0]["resultado"] == "trasladado"
    pasos = c.get(f"/reportes/{codigo}/seguimiento").json()["pasos"]
    assert pasos[4]["nombre"] == "Atendido · Lo trasladamos al refugio"


def test_solo_el_rescatista_asignado_y_en_el_sitio(c):
    codigo, _ = en_el_sitio(c, llegar=False)
    ana = sesion(c, ANA)
    assert informe(c, codigo, sesion(c, LUIS)).status_code == 403
    assert informe(c, codigo, sesion(c, VET)).status_code == 403
    assert informe(c, codigo, ana).status_code == 409  # todavía en camino
    c.post(f"/rescates/{codigo}/llegue", headers=ana)
    assert informe(c, codigo, ana).status_code == 201
    assert informe(c, codigo, ana).status_code == 409  # una sola vez


@pytest.mark.parametrize(("fotos", "campos", "mensaje"), [
    ((), {}, "al menos una foto"),
    ((JPEG,) * 4, {}, "hasta 3 fotos"),
    ((b"<html>no soy una foto</html>",), {}, "JPEG, PNG o WebP"),
    ((b"\xff\xd8\xff" + b"0" * (1024 * 1024),), {}, "1 MB"),
    ((JPEG,), {"accion": "no_rescatado"}, "por qué no se pudo"),
    ((JPEG,), {"nota": "x" * 501}, "500 caracteres"),
    ((JPEG,), {"accion": ""}, "qué se hizo"),
])
def test_se_rechaza_lo_que_no_vale(c, fotos, campos, mensaje):
    codigo, ana = en_el_sitio(c)
    respuesta = informe(c, codigo, ana, fotos=fotos, **campos)
    assert respuesta.status_code == 422 and mensaje in respuesta.json()["detail"]
    assert c.get("/rescates/mio", headers=ana).json()["estado"] == "en_sitio"  # no cambió nada


def test_no_estaba_no_exige_fotos_y_el_ciudadano_lo_ve_amable(c):
    codigo, ana = en_el_sitio(c)
    respuesta = informe(c, codigo, ana, fotos=(), encontrado="no_estaba", accion="")
    assert respuesta.status_code == 201 and respuesta.json()["resultado"] == "no_encontrado"
    pasos = c.get(f"/reportes/{codigo}/seguimiento").json()["pasos"]
    assert pasos[4]["nombre"] == "Atendido · No encontramos al animal en el lugar"


def test_no_se_pudo_rescatar_con_motivo(c):
    codigo, ana = en_el_sitio(c)
    assert informe(c, codigo, ana, accion="no_rescatado",
                   motivo="Se escapó hacia el caño antes de llegar").status_code == 201


def test_al_ciudadano_no_le_llegan_las_fotos_ni_la_nota(c):
    codigo, ana = en_el_sitio(c)
    informe(c, codigo, ana)
    texto = json.dumps(c.get(f"/reportes/{codigo}/seguimiento").json(), ensure_ascii=False)
    for privado in [NOTA, "/fotos/", "herido", "Ana", "asustado"]:
        assert privado not in texto


def test_las_fotos_solo_con_sesion_del_personal_del_caso(c):
    codigo, ana = en_el_sitio(c)
    foto = informe(c, codigo, ana).json()["fotos"][0]["url"]
    assert c.get(foto).status_code == 401
    assert c.get(foto, headers=sesion(c, "adop@correo.co")).status_code == 403
    assert c.get(foto, headers=sesion(c, LUIS)).status_code == 403  # otro rescatista
    for quien in (VET, COORD, ANA):
        respuesta = c.get(foto, headers=sesion(c, quien))
        assert respuesta.status_code == 200 and respuesta.content == JPEG
        assert respuesta.headers["x-content-type-options"] == "nosniff"
        assert respuesta.headers["content-type"] == "image/jpeg"
    assert c.get(f"/rescates/{codigo}/informe").status_code == 401
    assert c.get(f"/rescates/{codigo}/informe", headers=sesion(c, LUIS)).status_code == 403
    vistos = c.get("/rescates/informes", headers=sesion(c, COORD)).json()
    assert [(i["codigo"], i["nota"]) for i in vistos] == [(codigo, NOTA)]
    assert c.get("/rescates/informes", headers=ana).status_code == 403


def test_foto_del_reporte_con_la_clave_y_miniatura_en_la_cola(c):
    clave = "clave-del-reporte-0002"
    codigo = c.post("/reportes", headers={"Idempotency-Key": clave}, json={
        "descripcion": "Gata con una herida en la pata, cojea bastante",
        "direccion": "Calle 10"}).json()["codigo"]
    assert c.post(f"/reportes/{codigo}/foto", content=JPEG).status_code == 403  # sin clave
    assert c.post(f"/reportes/{codigo}/foto", content=b"<svg/>",
                  headers={"Idempotency-Key": clave}).status_code == 422
    assert c.post(f"/reportes/{codigo}/foto", content=JPEG,
                  headers={"Idempotency-Key": clave}).status_code == 201
    assert c.post(f"/reportes/{codigo}/foto", content=JPEG,
                  headers={"Idempotency-Key": clave}).status_code == 409  # una sola
    fila = next(r for r in c.get("/cola", headers=sesion(c, VET)).json() if r["codigo"] == codigo)
    assert fila["foto"].startswith("/fotos/")
    assert c.get(fila["foto"]).status_code == 401
    assert c.get(fila["foto"], headers=sesion(c, VET)).content == JPEG
    assert "/fotos/" not in json.dumps(c.get(f"/reportes/{codigo}/seguimiento").json())


def test_la_foto_del_reporte_de_mas_de_1_mb_se_rechaza(c):
    clave = "clave-del-reporte-0003"
    codigo = c.post("/reportes", headers={"Idempotency-Key": clave}, json={
        "descripcion": "Perro con una herida grande en el lomo, no camina", "direccion": "Calle 3"
    }).json()["codigo"]
    grande = b"\xff\xd8\xff" + b"0" * (1024 * 1024)
    respuesta = c.post(f"/reportes/{codigo}/foto", content=grande,
                       headers={"Idempotency-Key": clave})
    assert respuesta.status_code in (413, 422)
