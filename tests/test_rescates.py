"""HU-06, parte 1: rescatistas, ofertas y ciclo del rescate por la API (RF-05, RF-15, RN-08).

Comportamiento del prototipo (docs/prototipo/interaccion.js, rol Rescatista P-07 a P-09):
se ofrecen los reportes confirmados críticos o altos sin rescatista, solo a quien está
disponible; aceptar → en camino → llegué al sitio → resultado; liberar lo vuelve a ofrecer.
"""
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
CRITICO = "Perro atropellado en la avenida, está sangrando mucho"
LEVE = "Gato con sarna en el andén del barrio, se ve tranquilo"
CUENTAS = [("vet@patitas.co", Rol.VETERINARIO), ("coord@patitas.co", Rol.COORDINADOR),
           ("ana@rescate.co", Rol.RESCATISTA), ("luis@rescate.co", Rol.RESCATISTA)]


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    for correo, rol in CUENTAS:
        ServicioUsuarios(usuarios).registrar(correo, correo.split("@")[0], rol, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def reporte_confirmado(c, descripcion=CRITICO, prioridad=None):
    codigo = c.post("/reportes", json={"descripcion": descripcion,
                                       "direccion": "Calle 8 con Av. 4"}).json()["codigo"]
    datos = {} if prioridad is None else {"prioridad": prioridad,
                                          "justificacion": "Ajuste revisado en la prueba"}
    c.post(f"/reportes/{codigo}/confirmacion", json=datos,
           headers=sesion(c, "vet@patitas.co"))
    return codigo


def disponible(c, correo="ana@rescate.co"):
    cabeceras = sesion(c, correo)
    c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=cabeceras)
    return cabeceras


def test_no_disponible_no_recibe_ofertas(c):
    reporte_confirmado(c)
    assert c.get("/rescates/ofertas", headers=sesion(c, "ana@rescate.co")).json() == []


def test_ofertas_solo_de_confirmados_criticos_o_altos(c):
    critico = reporte_confirmado(c)
    alto = reporte_confirmado(c, LEVE, prioridad="alta")
    reporte_confirmado(c, LEVE)  # confirmado bajo: lo atiende el refugio, no un rescate
    c.post("/reportes", json={"descripcion": CRITICO, "direccion": "Calle 1"})  # pendiente
    ofertas = c.get("/rescates/ofertas", headers=disponible(c)).json()
    assert [o["codigo"] for o in ofertas] == [critico, alto]
    assert set(ofertas[0]) == {"codigo", "prioridad", "descripcion", "esperando_desde"}


def test_ciclo_completo_aceptar_llegue_resultado(c):
    codigo = reporte_confirmado(c)
    ana = disponible(c)
    aceptado = c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    assert aceptado.status_code == 200
    assert aceptado.json()["estado"] == "en_camino"
    assert aceptado.json()["ubicacion"]["direccion"] == "Calle 8 con Av. 4"
    assert c.get("/rescates/ofertas", headers=disponible(c, "luis@rescate.co")).json() == []
    assert c.post(f"/rescates/{codigo}/llegue", headers=ana).json()["estado"] == "en_sitio"
    final = c.post(f"/rescates/{codigo}/resultado", json={"resultado": "trasladado"},
                   headers=ana)
    assert final.json() == {"codigo": codigo, "estado": "atendido", "resultado": "trasladado"}
    assert c.get("/rescates/mio", headers=ana).json() is None


def test_rn08_otro_rescatista_ya_lo_tomo(c):
    codigo = reporte_confirmado(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=disponible(c))
    respuesta = c.post(f"/rescates/{codigo}/aceptar", headers=disponible(c, "luis@rescate.co"))
    assert respuesta.status_code == 409
    assert "Otro rescatista ya tomó este rescate" in respuesta.json()["detail"]


def test_rn08_ya_tienes_un_rescate_activo(c):
    primero, segundo = reporte_confirmado(c), reporte_confirmado(c)
    ana = disponible(c)
    c.post(f"/rescates/{primero}/aceptar", headers=ana)
    respuesta = c.post(f"/rescates/{segundo}/aceptar", headers=ana)
    assert respuesta.status_code == 409
    assert "RN-08" in respuesta.json()["detail"]
    assert c.get("/rescates/mio", headers=ana).json()["codigo"] == primero


def test_liberar_lo_vuelve_a_ofrecer(c):
    codigo = reporte_confirmado(c)
    ana = disponible(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    assert c.post(f"/rescates/{codigo}/liberar", headers=ana).status_code == 200
    luis = disponible(c, "luis@rescate.co")
    assert [o["codigo"] for o in c.get("/rescates/ofertas", headers=luis).json()] == [codigo]


def test_resultado_antes_de_llegar_se_rechaza(c):
    codigo = reporte_confirmado(c)
    ana = disponible(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    respuesta = c.post(f"/rescates/{codigo}/resultado", json={"resultado": "trasladado"},
                       headers=ana)
    assert respuesta.status_code == 409
    assert "Llegué al sitio" in respuesta.json()["detail"]


def test_pasos_sobre_un_rescate_ajeno_o_sin_aceptar_se_rechazan(c):
    codigo = reporte_confirmado(c)
    assert c.post(f"/rescates/{codigo}/llegue", headers=disponible(c)).status_code == 409
    c.post(f"/rescates/{codigo}/aceptar", headers=disponible(c))
    luis = disponible(c, "luis@rescate.co")
    assert c.post(f"/rescates/{codigo}/llegue", headers=luis).status_code == 409
    assert c.post(f"/rescates/{codigo}/liberar", headers=luis).status_code == 409


def test_aceptar_sin_estar_disponible_o_algo_que_no_se_ofrece(c):
    critico = reporte_confirmado(c)
    bajo = reporte_confirmado(c, LEVE)
    no_disponible = c.post(f"/rescates/{critico}/aceptar", headers=sesion(c, "ana@rescate.co"))
    assert no_disponible.status_code == 409
    assert "disponible" in no_disponible.json()["detail"]
    assert c.post(f"/rescates/{bajo}/aceptar", headers=disponible(c)).status_code == 404
    assert c.post("/rescates/NOEXISTE/aceptar", headers=disponible(c)).status_code == 404


def test_resultado_desconocido_da_422(c):
    codigo = reporte_confirmado(c)
    ana = disponible(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    c.post(f"/rescates/{codigo}/llegue", headers=ana)
    assert c.post(f"/rescates/{codigo}/resultado", json={"resultado": "perdido"},
                  headers=ana).status_code == 422


@pytest.mark.parametrize("correo", ["vet@patitas.co", "coord@patitas.co"])
def test_solo_rescatistas_usan_los_rescates(c, correo):
    otro = sesion(c, correo)
    assert c.get("/rescates/ofertas", headers=otro).status_code == 403
    assert c.put("/rescatistas/yo/disponibilidad", json={"disponible": True},
                 headers=otro).status_code == 403
    assert c.get("/rescates/ofertas").status_code == 401


def test_el_rescatista_no_ve_la_cola_del_veterinario(c):
    assert c.get("/cola", headers=sesion(c, "ana@rescate.co")).status_code == 403
