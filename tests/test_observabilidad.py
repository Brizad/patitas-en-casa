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


def _app(monkeypatch, **entorno):
    for nombre in ("PATITAS_OBSERVABILIDAD", "PATITAS_METRICAS_TOKEN"):
        monkeypatch.delenv(nombre, raising=False)
    for nombre, valor in entorno.items():
        monkeypatch.setenv(nombre, valor)
    cupos = RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", capacidad=40))
    return crear_app(RepositorioEnMemoria(), cupos,
                     repositorio_usuarios=RepositorioUsuariosEnMemoria(),
                     emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres"))


def test_apagada_por_defecto_no_hay_metricas_y_el_contrato_no_cambia(monkeypatch):
    apagada = _app(monkeypatch)
    assert TestClient(apagada).get("/metrics").status_code == 404
    encendida = _app(monkeypatch, PATITAS_OBSERVABILIDAD="1", PATITAS_METRICAS_TOKEN="t" * 32)
    assert apagada.openapi() == encendida.openapi()  # /metrics no entra al OpenAPI


def test_sin_token_las_metricas_no_se_exponen_aunque_este_activada(monkeypatch):
    """Falla segura: activar la observabilidad y olvidar el token no deja /metrics pública."""
    c = TestClient(_app(monkeypatch, PATITAS_OBSERVABILIDAD="1"))
    assert c.get("/metrics").status_code == 404
    assert c.get("/metrics", headers={"Authorization": "Bearer "}).status_code == 404


def test_un_token_con_tildes_no_rompe_la_comparacion(monkeypatch):
    c = TestClient(_app(monkeypatch, PATITAS_OBSERVABILIDAD="1", PATITAS_METRICAS_TOKEN="t" * 32))
    raro = "Bearer ñandú".encode("latin-1")  # así llega del navegador un encabezado con tildes
    assert c.get("/metrics", headers={"Authorization": raro}).status_code == 401


def test_apagada_no_se_carga_el_sdk_de_opentelemetry():
    import subprocess
    import sys
    codigo = ("import sys, app.observabilidad; "
              "print(any(m.startswith(('opentelemetry.sdk', 'prometheus_client')) "
              "for m in sys.modules))")
    assert subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                          check=True).stdout.strip() == "False"
