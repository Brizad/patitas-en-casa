"""Pruebas de caja negra de la API: solo entradas y salidas (trazadas a HU-01, HU-02, HU-03)."""
from fastapi.testclient import TestClient

from app.api.main import crear_app

REPORTE = {"descripcion": "Perro atropellado en la avenida, está sangrando mucho",
           "latitud": 7.8939, "longitud": -72.5078}


def cliente():
    return TestClient(crear_app())


def test_cp01a_reporte_sin_cuenta_devuelve_codigo():
    respuesta = cliente().post("/reportes", json=REPORTE)
    assert respuesta.status_code == 201
    assert len(respuesta.json()["codigo"]) == 8


def test_cp01b_video_de_75_segundos_se_rechaza():
    respuesta = cliente().post("/reportes", json={**REPORTE, "video_segundos": 75})
    assert respuesta.status_code == 422
    assert "60 segundos" in respuesta.json()["detail"]


def test_cp04c_ciudadano_no_ve_la_cola():
    assert cliente().get("/cola", headers={"X-Rol": "ciudadano"}).status_code == 403


def test_cp04a_reporte_critico_aparece_primero():
    c = cliente()
    c.post("/reportes", json={**REPORTE, "descripcion": "Gato con sarna en el andén del barrio"})
    critico = c.post("/reportes", json=REPORTE).json()["codigo"]
    cola = c.get("/cola", headers={"X-Rol": "veterinario"}).json()
    assert cola[0]["codigo"] == critico
    assert cola[0]["prioridad"] == "critica"


def test_consulta_de_estado_con_codigo_invalido():
    assert cliente().get("/reportes/NOEXISTE").status_code == 404


def test_cp07a_ingreso_actualiza_ocupacion():
    ingreso = {"nombre": "Canela", "especie": "gato", "estado_salud": "desnutrición leve"}
    respuesta = cliente().post("/refugio/ingresos", json=ingreso)
    assert respuesta.status_code == 201
    assert respuesta.json()["ocupacion"] == "1/40"
