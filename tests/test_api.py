"""Pruebas de caja negra de la API: solo entradas y salidas (trazadas a HU-01, HU-02, HU-03)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.api.seguridad import crear_dependencia_usuario, exigir_rol
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

REPORTE = {"descripcion": "Perro atropellado en la avenida, está sangrando mucho",
           "latitud": 7.8939, "longitud": -72.5078}
INGRESO = {"nombre": "Canela", "especie": "gato", "estado_salud": "desnutrición leve"}
# Valores falsos, solo para pruebas.
SECRETO_PRUEBAS = "secreto-de-pruebas-con-mas-de-32-caracteres"
CLAVE = "clave-de-prueba-larga"


def cliente():
    """Repositorios en memoria con una veterinaria y una coordinadora registradas."""
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    cupos = RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", capacidad=40))
    return TestClient(crear_app(RepositorioEnMemoria(), cupos, repositorio_usuarios=usuarios,
                                emisor_tokens=EmisorTokens(SECRETO_PRUEBAS)))


def sesion(c, correo="vet@patitas.co"):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def test_cp01a_reporte_sin_cuenta_devuelve_codigo():
    respuesta = cliente().post("/reportes", json=REPORTE)
    assert respuesta.status_code == 201
    assert len(respuesta.json()["codigo"]) == 8


def test_cp01b_video_de_75_segundos_se_rechaza():
    respuesta = cliente().post("/reportes", json={**REPORTE, "video_segundos": 75})
    assert respuesta.status_code == 422
    assert "60 segundos" in respuesta.json()["detail"]


def test_cp04c_ciudadano_no_ve_la_cola():
    """Sin sesión de personal la cola no se muestra (DT-02: antes bastaba con X-Rol)."""
    assert cliente().get("/cola").status_code == 401


def test_dt02_el_encabezado_x_rol_ya_no_da_acceso():
    respuesta = cliente().get("/cola", headers={"X-Rol": "veterinario"})
    assert respuesta.status_code == 401
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_cp04a_reporte_critico_aparece_primero():
    c = cliente()
    c.post("/reportes", json={**REPORTE, "descripcion": "Gato con sarna en el andén del barrio"})
    critico = c.post("/reportes", json=REPORTE).json()["codigo"]
    cola = c.get("/cola", headers=sesion(c)).json()
    assert cola[0]["codigo"] == critico
    assert cola[0]["prioridad"] == "critica"


def test_consulta_de_estado_con_codigo_invalido():
    assert cliente().get("/reportes/NOEXISTE").status_code == 404


def test_consulta_de_estado_es_publica_para_el_ciudadano():
    c = cliente()
    codigo = c.post("/reportes", json=REPORTE).json()["codigo"]
    assert c.get(f"/reportes/{codigo}").status_code == 200


def test_cp07a_ingreso_actualiza_ocupacion():
    c = cliente()
    respuesta = c.post("/refugio/ingresos", json=INGRESO, headers=sesion(c, "coord@patitas.co"))
    assert respuesta.status_code == 201
    assert respuesta.json()["ocupacion"] == "1/40"


@pytest.mark.parametrize("metodo, ruta", [
    ("get", "/cola"), ("post", "/refugio/ingresos"), ("get", "/refugio/ocupacion"),
])
def test_endpoints_del_personal_exigen_sesion(metodo, ruta):
    c = cliente()
    kwargs = {"json": INGRESO} if metodo == "post" else {}
    assert getattr(c, metodo)(ruta, **kwargs).status_code == 401
    assert getattr(c, metodo)(ruta, headers=sesion(c), **kwargs).status_code in (200, 201)


def test_ingreso_sin_sesion_no_ocupa_cupo():
    c = cliente()
    c.post("/refugio/ingresos", json=INGRESO)
    assert c.get("/refugio/ocupacion", headers=sesion(c)).json()["ocupacion"] == "0/40"


def test_exigir_rol_responde_403_al_rol_no_permitido():
    """Base para endpoints de un solo rol: veterinaria con sesión válida, ruta de coordinación."""
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    emisor = EmisorTokens(SECRETO_PRUEBAS)
    solo_coordinacion = exigir_rol(crear_dependencia_usuario(usuarios, emisor), Rol.COORDINADOR)
    app = FastAPI()
    app.get("/solo-coordinacion", dependencies=[solo_coordinacion])(lambda: {"ok": True})
    token = emisor.emitir(usuarios.buscar_por_correo("vet@patitas.co"))
    respuesta = TestClient(app).get("/solo-coordinacion",
                                    headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403
