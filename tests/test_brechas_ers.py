"""Brechas del ERS cerradas en #108: RF-07, RF-13, RF-14, RF-16, RF-29."""
import pytest

from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Rol
from app.refugios.repositorio_postgres import RepositorioRefugiosPostgres
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios
from tests.test_decision_adopcion import CLAVE, en_memoria, h, preparar


def con_cuenta(c, correo, rol):
    usuarios = c.app.state.usuarios
    ServicioUsuarios(usuarios).registrar(correo, "X", rol, CLAVE)


def test_rf13_la_alcaldia_solo_ve_indicadores_anonimizados():
    c = en_memoria()
    con_cuenta(c, "alcaldia@cucuta.gov.co", Rol.ALCALDIA)
    alc = h(c, "alcaldia@cucuta.gov.co")
    assert c.get("/indicadores", headers=alc).status_code == 200
    assert c.get("/indicadores/reportes.csv", headers=alc).status_code == 200
    for ruta in ("/cola", "/refugio/animales", "/refugio/solicitudes", "/bitacora"):
        assert c.get(ruta, headers=alc).status_code == 403


def test_rf14_el_refugio_guarda_su_direccion():
    c = en_memoria()
    con_cuenta(c, "admin@patitas.co", Rol.ADMINISTRADOR)
    r = c.post("/admin/refugios", json={"nombre": "Huellitas", "capacidad": 20,
                                        "direccion": " Calle 5 # 2-30 "},
               headers=h(c, "admin@patitas.co"))
    assert r.json()["direccion"] == "Calle 5 # 2-30"


def test_rf16_el_administrador_consulta_el_historial_de_acceso():
    c = en_memoria()
    con_cuenta(c, "admin@patitas.co", Rol.ADMINISTRADOR)
    h(c, "coord@patitas.co")
    h(c, "coord@patitas.co")
    accesos = c.get("/admin/usuarios/coord@patitas.co/accesos",
                    headers=h(c, "admin@patitas.co")).json()
    assert len(accesos) == 2 and accesos[0]["momento"].endswith("+00:00")


def test_rf29_el_compromiso_lleva_los_datos_del_refugio():
    c = en_memoria()
    coord, _, ids = preparar(c)
    sid = ids["lau@correo.co"]
    c.post(f"/refugio/solicitudes/{sid}/decision", json={"aprobar": True}, headers=coord)
    pdf = c.get(f"/adopciones/solicitudes/{sid}/compromiso.pdf", headers=coord).content
    assert b"Refugio: Demo" in pdf


class NotificadorEspia:
    def __init__(self):
        self.enviados = []

    def enviar(self, destinatario, mensaje):
        self.enviados.append(destinatario)


@pytest.mark.postgres
def test_rf07_la_alerta_va_a_los_coordinadores_de_ese_refugio(bd_limpia):
    from fastapi.testclient import TestClient

    from app.api.main import crear_app
    usuarios = RepositorioUsuariosPostgres(bd_limpia)
    norte = RepositorioRefugiosPostgres(bd_limpia).crear("Norte", 1)
    for correo, refugio in (("a@patitas.co", norte.id), ("b@patitas.co", norte.id),
                            ("otro@patitas.co", 1)):
        ServicioUsuarios(usuarios).registrar(correo, "X", Rol.COORDINADOR, CLAVE)
        usuarios.vincular_refugio(correo, refugio)
    espia = NotificadorEspia()
    c = TestClient(crear_app(RepositorioPostgres(bd_limpia),
                             RepositorioCuposPostgres.primer_refugio(bd_limpia),
                             repositorio_usuarios=usuarios, notificador=espia,
                             emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-c")))
    c.post("/refugio/ingresos", json={"nombre": "Luna", "especie": "gato",
                                      "estado_salud": "sana"}, headers=h(c, "a@patitas.co"))
    assert sorted(espia.enviados) == ["a@patitas.co", "b@patitas.co"]
