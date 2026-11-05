"""P-12 (#285): aviso opcional al dueño de un correo con el que alguien intenta registrarse."""
from fastapi.testclient import TestClient

from app import config
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from tests.test_api import CLAVE, SECRETO_PRUEBAS

CUENTA = {"correo": "Lau@Correo.co", "nombre": "Laura", "contrasena": CLAVE,
          "autoriza_datos": True}


class Espia:
    def __init__(self, falla: bool = False) -> None:
        self.enviados: list[tuple[str, str]] = []
        self.falla = falla

    def enviar(self, destinatario: str, mensaje: str) -> None:
        if self.falla:
            raise ConnectionError("Mailjet caído")
        self.enviados.append((destinatario, mensaje))


def _cliente(espia: Espia) -> TestClient:
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio", capacidad=10)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens(SECRETO_PRUEBAS), notificador=espia))


def test_por_defecto_no_se_avisa_a_nadie():
    assert config.AVISAR_REGISTRO_DUPLICADO is False
    espia = Espia()
    c = _cliente(espia)
    c.post("/adoptantes", json=CUENTA)
    c.post("/adoptantes", json=CUENTA)
    assert espia.enviados == []


def test_activado_se_avisa_solo_al_repetir_y_la_respuesta_es_la_misma(monkeypatch):
    monkeypatch.setattr(config, "AVISAR_REGISTRO_DUPLICADO", True)
    espia = Espia()
    c = _cliente(espia)
    primera = c.post("/adoptantes", json=CUENTA)
    assert espia.enviados == []  # una cuenta nueva no recibe este aviso
    segunda = c.post("/adoptantes", json={**CUENTA, "nombre": "Otra persona"})
    assert (primera.status_code, primera.json()) == (segunda.status_code, segunda.json())
    assert len(espia.enviados) == 1
    destinatario, mensaje = espia.enviados[0]
    assert destinatario == "lau@correo.co"
    assert "no cambió" in mensaje and CLAVE not in mensaje


def test_si_el_correo_falla_el_registro_igual_responde(monkeypatch):
    monkeypatch.setattr(config, "AVISAR_REGISTRO_DUPLICADO", True)
    c = _cliente(Espia(falla=True))
    c.post("/adoptantes", json=CUENTA)
    assert c.post("/adoptantes", json=CUENTA).status_code == 201
