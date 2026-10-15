"""HU-08: el ciudadano sigue su reporte con el código, sin datos personales (RF-11, RN-14).

Línea de tiempo tomada del prototipo (docs/prototipo/interaccion.js, "3. Consultar estado").
"""
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
CRITICO = "Perro atropellado en la avenida, está sangrando mucho"
LEVE = "Gato con sarna en el andén del barrio, se ve tranquilo"
DIRECCION = "Calle 8 con Av. 4 frente a la panadería"


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    for correo, rol in [("vet@patitas.co", Rol.VETERINARIO),
                        ("ana@rescate.co", Rol.RESCATISTA)]:
        ServicioUsuarios(usuarios).registrar(correo, "Persona", rol, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def reportar(c, descripcion=CRITICO):
    return c.post("/reportes", json={"descripcion": descripcion, "direccion": DIRECCION,
                                     "latitud": 7.8939, "longitud": -72.5078}).json()["codigo"]


def confirmar(c, codigo):
    c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=sesion(c, "vet@patitas.co"))


def rescatista(c):
    cabeceras = sesion(c, "ana@rescate.co")
    c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=cabeceras)
    return cabeceras


def seguimiento(c, codigo):
    respuesta = c.get(f"/reportes/{codigo}/seguimiento")
    assert respuesta.status_code == 200
    return respuesta.json()


def resumen(datos):
    """[(nombre, estado, detalle)] para comparar sin fechas."""
    return [(p["nombre"], p["estado"], p["detalle"]) for p in datos["pasos"]]


def test_recien_recibido(c):
    datos = seguimiento(c, reportar(c))
    assert resumen(datos) == [
        ("Recibido", "hecho", None),
        ("Revisado por el veterinario", "actual", None),
        ("Rescatista en camino", "pendiente", None),
        ("Atendido", "pendiente", None),
        ("Cerrado", "pendiente", None),
    ]
    assert datos["pasos"][0]["fecha"] == datos["ultimo_cambio"]


def test_confirmado_critico_busca_rescatista(c):
    codigo = reportar(c)
    confirmar(c, codigo)
    pasos = resumen(seguimiento(c, codigo))
    assert pasos[1][1] == "hecho"
    assert pasos[2] == ("Rescatista en camino", "actual", "Buscando rescatista disponible")


def test_confirmado_leve_lo_programa_el_refugio(c):
    codigo = reportar(c, LEVE)
    confirmar(c, codigo)
    assert resumen(seguimiento(c, codigo))[2] == (
        "Atención programada por el refugio", "actual", None)


def test_rescatista_en_camino_y_en_el_sitio(c):
    codigo = reportar(c)
    confirmar(c, codigo)
    ana = rescatista(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    assert resumen(seguimiento(c, codigo))[2] == ("Rescatista en camino", "actual", None)
    c.post(f"/rescates/{codigo}/llegue", headers=ana)
    pasos = resumen(seguimiento(c, codigo))
    assert pasos[2][1] == "hecho"
    assert pasos[3] == ("Atendido", "actual", "Rescatista en el sitio")


def test_atendido_cierra_la_linea_de_tiempo(c):
    codigo = reportar(c)
    confirmar(c, codigo)
    ana = rescatista(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    c.post(f"/rescates/{codigo}/llegue", headers=ana)
    c.post(f"/rescates/{codigo}/resultado", json={"resultado": "trasladado"}, headers=ana)
    datos = seguimiento(c, codigo)
    assert [p["estado"] for p in datos["pasos"]] == ["hecho"] * 5
    assert datos["pasos"][3]["nombre"] == "Atendido · Trasladado a refugio"
    assert datos["ultimo_cambio"] == max(p["fecha"] for p in datos["pasos"] if p["fecha"])


def test_liberado_vuelve_a_buscar_rescatista(c):
    codigo = reportar(c)
    confirmar(c, codigo)
    ana = rescatista(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    c.post(f"/rescates/{codigo}/liberar", headers=ana)
    assert resumen(seguimiento(c, codigo))[2][2] == "Buscando rescatista disponible"


def test_rn14_no_muestra_datos_personales_ni_detalles_del_caso(c):
    codigo = reportar(c)
    confirmar(c, codigo)
    ana = rescatista(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    texto = json.dumps(seguimiento(c, codigo), ensure_ascii=False)
    for dato in ["atropellado", DIRECCION, "Calle 8", "7.89", "-72.5", "critica",
                 "vet@patitas.co", "ana@rescate.co", "confianza"]:
        assert dato not in texto
    assert set(seguimiento(c, codigo)) == {"codigo", "ultimo_cambio", "pasos"}


def test_codigo_inexistente_404_y_formato_flexible(c):
    assert c.get("/reportes/NOEXISTE/seguimiento").status_code == 404
    codigo = reportar(c)
    assert c.get(f"/reportes/{codigo.lower()}/seguimiento").status_code == 200
    assert c.get(f"/reportes/{codigo[:4]} {codigo[4:]}/seguimiento").status_code == 200


def test_la_consulta_de_estado_anterior_no_cambia(c):
    codigo = reportar(c)
    assert c.get(f"/reportes/{codigo}").json() == {"codigo": codigo, "estado": "clasificado"}
