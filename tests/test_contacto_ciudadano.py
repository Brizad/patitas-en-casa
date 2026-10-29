"""RF-18 y RNF-08 (#111): contacto opcional del ciudadano, con autorización y cifrado."""
import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.cifrado import CanalConDescifrado, Cifrador
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE_DATOS = "clave-de-datos-de-pruebas-con-mas-de-32-caracteres"  # falsa
CLAVE = "clave-de-prueba-larga"  # falsa
REPORTE = {"descripcion": "Perro atropellado en la avenida, no se mueve y sangra",
           "direccion": "Avenida 0 # 10-20"}


class Espia:
    def __init__(self):
        self.enviados = []

    def entregar(self, destinatario, mensaje):
        self.enviados.append((destinatario, mensaje))


def test_cifrar_y_descifrar_y_detectar_alteraciones():
    c = Cifrador(CLAVE_DATOS)
    a, b = c.cifrar("lau@correo.co"), c.cifrar("lau@correo.co")
    assert a != b and "lau" not in a  # cada cifrado es distinto e ilegible
    assert c.descifrar(a) == "lau@correo.co"
    with pytest.raises(InvalidTag):
        Cifrador("otra-clave-de-pruebas-con-mas-de-32-caracteres").descifrar(a)
    with pytest.raises(ValueError):
        Cifrador("corta")


def app_con(espia):
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana", Rol.VETERINARIO, CLAVE)
    repo = RepositorioEnMemoria()
    c = TestClient(crear_app(repo, RepositorioCuposEnMemoria(Refugio("Demo", 40)),
                             repositorio_usuarios=usuarios, notificador=espia,
                             emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-c"),
                             cifrador=Cifrador(CLAVE_DATOS)))
    return c, repo


def test_contacto_sin_autorizacion_se_rechaza():
    c, _ = app_con(Espia())
    r = c.post("/reportes", json={**REPORTE, "contacto": "lau@correo.co"})
    assert r.status_code == 422 and "autoriz" in r.json()["detail"]


def test_contacto_invalido_se_rechaza():
    c, _ = app_con(Espia())
    r = c.post("/reportes", json={**REPORTE, "contacto": "no sé", "autoriza_contacto": True})
    assert r.status_code == 422


def test_el_contacto_se_guarda_cifrado_y_recibe_un_aviso_al_revisarse():
    espia = Espia()
    c, repo = app_con(espia)
    codigo = c.post("/reportes", json={**REPORTE, "contacto": "Lau@Correo.co",
                                       "autoriza_contacto": True}).json()["codigo"]
    guardado = repo.buscar(codigo)
    assert guardado.contacto_cifrado and "lau" not in guardado.contacto_cifrado
    t = c.post("/auth/token", data={"username": "vet@patitas.co", "password": CLAVE}).json()
    c.post(f"/reportes/{codigo}/confirmacion", json={},
           headers={"Authorization": f"Bearer {t['access_token']}"})
    avisos = repo.avisos.de_reporte(codigo)
    assert any(a.destinatario.startswith("cifrado:") for a in avisos)
    assert all("lau" not in a.destinatario for a in avisos)  # la tabla tampoco lo tiene
    c.app.state.procesador_avisos.procesar()
    al_ciudadano = [m for d, m in espia.enviados if d == "lau@correo.co"]
    assert al_ciudadano and codigo in al_ciudadano[0]
    assert "critica" not in al_ciudadano[0].lower()  # sin prioridad ni detalles (RN-14)
    seguimiento = c.get(f"/reportes/{codigo}/seguimiento").text
    assert "lau" not in seguimiento


def test_un_telefono_se_guarda_pero_no_genera_aviso_por_correo():
    c, repo = app_con(Espia())
    codigo = c.post("/reportes", json={**REPORTE, "contacto": "300 123 4567",
                                       "autoriza_contacto": True}).json()["codigo"]
    assert Cifrador(CLAVE_DATOS).descifrar(repo.buscar(codigo).contacto_cifrado) == "3001234567"


def test_el_canal_descifra_solo_los_destinatarios_cifrados():
    espia, cif = Espia(), Cifrador(CLAVE_DATOS)
    canal = CanalConDescifrado(espia, cif)
    canal.entregar("cifrado:" + cif.cifrar("a@b.co"), "hola")
    canal.entregar("rescatista@patitas.co", "hola")
    assert [d for d, _ in espia.enviados] == ["a@b.co", "rescatista@patitas.co"]


@pytest.mark.postgres
def test_en_la_base_no_queda_el_contacto_en_claro(bd_limpia):
    from app.reportes.repositorio_postgres import RepositorioPostgres
    c = TestClient(crear_app(RepositorioPostgres(bd_limpia),
                             RepositorioCuposEnMemoria(Refugio("Demo", 40)),
                             repositorio_usuarios=RepositorioUsuariosEnMemoria(),
                             emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-c"),
                             cifrador=Cifrador(CLAVE_DATOS)))
    c.post("/reportes", json={**REPORTE, "contacto": "lau@correo.co", "autoriza_contacto": True})
    with bd_limpia.connect() as conexion:
        volcado = str(conexion.execute(text("SELECT * FROM reportes")).all())
    assert "lau@correo.co" not in volcado
