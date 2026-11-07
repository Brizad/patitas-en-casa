"""FPI-29: la telemetría existe y nunca contiene datos personales."""
import json
import logging

from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.observabilidad import FormatoJSON, evento
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria

DESCRIPCION = "Perro atropellado frente a la casa de Doña Rosa, sangra mucho"


def _cliente(monkeypatch):
    monkeypatch.setenv("PATITAS_OBSERVABILIDAD", "1")
    monkeypatch.setenv("PATITAS_METRICAS_TOKEN", "token-de-pruebas")
    cupos = RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", capacidad=40))
    return TestClient(crear_app(RepositorioEnMemoria(), cupos,
                                repositorio_usuarios=RepositorioUsuariosEnMemoria(),
                                emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def test_log_json_descarta_campos_personales(caplog):
    registro = logging.LogRecord("patitas.eventos", logging.INFO, "", 0, "reporte_creado", (), None)
    registro.datos = {"codigo": "ABC12345", "descripcion": DESCRIPCION, "latitud": 7.89,
                      "contacto": "3001234567", "cedula": "1092526077", "comuna": 3}
    linea = json.loads(FormatoJSON().format(registro))
    assert linea["evento"] == "reporte_creado" and linea["codigo"] == "ABC12345"
    assert not {"descripcion", "latitud", "contacto", "cedula"} & set(linea)


def test_metricas_protegidas_y_sin_codigos_de_reporte(monkeypatch):
    c = _cliente(monkeypatch)
    r = c.post("/reportes", json={"descripcion": DESCRIPCION, "latitud": 7.89,
                                  "longitud": -72.5, "comuna": 3})
    assert r.status_code == 201
    codigo = r.json()["codigo"]
    c.get(f"/reportes/{codigo}/seguimiento")
    assert c.get("/metrics").status_code == 401
    texto = c.get("/metrics", headers={"Authorization": "Bearer token-de-pruebas"}).text
    assert "http_server_duration" in texto and 'http_route="/reportes"' in texto
    assert 'http_route="/reportes/{codigo}/seguimiento"' in texto
    assert codigo not in texto and "Rosa" not in texto and "7.89" not in texto


def test_evento_no_falla_sin_observabilidad():
    evento("prueba", codigo="X")
