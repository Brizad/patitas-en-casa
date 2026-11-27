"""#498: el rescatista comparte su ubicación en camino y el ciudadano lo ve en el mapa; recorrido
de demostración solo para las cuentas de demostración."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.rescates.distancia import (
    LLEGANDO_M,
    desplazar,
    haversine_m,
    minutos_aprox,
    redondear,
)
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
ANIMAL = (7.8939, -72.5078)
ANA, LUIS, DEMO = "ana@rescate.co", "luis@rescate.co", "rescatista@demo.patitas.co"


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    servicio = ServicioUsuarios(usuarios)
    servicio.registrar("vet@patitas.co", "Dra. Vet", Rol.VETERINARIO, CLAVE)
    servicio.registrar(ANA, "Ana María Ruiz", Rol.RESCATISTA, CLAVE)
    servicio.registrar(LUIS, "Luis Peña", Rol.RESCATISTA, CLAVE)
    servicio.registrar(DEMO, "Rita Gómez (demo)", Rol.RESCATISTA, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def en_camino(c, rescatista=ANA):
    """Reporte crítico con GPS, confirmado y aceptado por `rescatista`."""
    codigo = c.post("/reportes", json={
        "descripcion": "Perro atropellado en la avenida, está sangrando mucho",
        "latitud": ANIMAL[0], "longitud": ANIMAL[1]}).json()["codigo"]
    c.post(f"/reportes/{codigo}/confirmacion", headers=sesion(c, "vet@patitas.co"),
           json={"prioridad": "critica", "justificacion": "Sangra mucho y no se mueve"})
    cabeceras = sesion(c, rescatista)
    c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=cabeceras)
    assert c.post(f"/rescates/{codigo}/aceptar", headers=cabeceras).status_code == 200
    return codigo, cabeceras


def ubicar(c, codigo, cabeceras, lat, lon):
    return c.put(f"/rescates/{codigo}/ubicacion", json={"latitud": lat, "longitud": lon},
                 headers=cabeceras)


def mapa(c, codigo):
    return c.get(f"/reportes/{codigo}/seguimiento").json().get("rescatista")


# --- Distancia -----------------------------------------------------------------------------

def test_haversine_y_tiempo_a_25_km_por_hora():
    lejos = desplazar(*ANIMAL, 1200, 0)
    assert abs(haversine_m(*lejos, *ANIMAL) - 1200) < 5
    assert minutos_aprox(1200) == 3  # 1,2 km a 25 km/h ≈ 2,9 min
    assert minutos_aprox(50) == 1
    assert redondear(7.89412) == 7.8939  # rejilla de ~50 m


# --- Compartir --------------------------------------------------------------------------

def test_solo_el_rescatista_asignado_envia_la_ubicacion(c):
    codigo, ana = en_camino(c)
    assert ubicar(c, codigo, sesion(c, LUIS), 7.9, -72.5).status_code == 403
    assert c.put(f"/rescates/{codigo}/ubicacion", json={"latitud": 7.9, "longitud": -72.5}
                 ).status_code == 401
    assert ubicar(c, codigo, sesion(c, "vet@patitas.co"), 7.9, -72.5).status_code == 403
    assert ubicar(c, codigo, ana, 7.9, -72.5).status_code == 200
    assert ubicar(c, codigo, ana, 95, -72.5).status_code == 422  # fuera de rango


def test_el_ciudadano_ve_distancia_y_minutos_con_posicion_redondeada(c):
    codigo, ana = en_camino(c)
    assert mapa(c, codigo)["ubicacion"] is None  # aún no comparte
    lat, lon = desplazar(*ANIMAL, 1200, 90)
    ubicar(c, codigo, ana, lat, lon)
    datos = mapa(c, codigo)
    assert abs(datos["distancia_m"] - 1200) < 10 and datos["minutos"] == 3
    assert datos["ubicacion"] == {"latitud": redondear(lat), "longitud": redondear(lon)}
    assert datos["animal"] == {"latitud": redondear(ANIMAL[0]), "longitud": redondear(ANIMAL[1])}
    assert datos["nombre"] == "Ana" and datos["simulada"] is False
    ubicar(c, codigo, ana, *desplazar(*ANIMAL, 200, 90))
    assert mapa(c, codigo)["distancia_m"] < LLEGANDO_M  # «¡Está llegando!»


def test_el_ciudadano_no_recibe_correo_ni_telefono(c):
    codigo, ana = en_camino(c)
    ubicar(c, codigo, ana, 7.9, -72.5)
    texto = json.dumps(c.get(f"/reportes/{codigo}/seguimiento").json(), ensure_ascii=False)
    assert "@" not in texto and ANA not in texto and "Ruiz" not in texto


@pytest.mark.parametrize("pasos", [["llegue"], ["llegue", "resultado"], ["liberar"]])
def test_la_ubicacion_se_borra_al_llegar_atender_o_liberar(c, pasos):
    codigo, ana = en_camino(c)
    ubicar(c, codigo, ana, 7.9, -72.5)
    for paso in pasos:
        if paso == "resultado":
            c.post(f"/rescates/{codigo}/resultado", json={"resultado": "atendido_en_sitio"},
                   headers=ana)
        else:
            c.post(f"/rescates/{codigo}/{paso}", headers=ana)
    assert mapa(c, codigo) is None  # el mapa desaparece: ya no va en camino
    assert c.app.state.demo_servicios[2]._rescates.ubicacion(codigo) is None
    assert ubicar(c, codigo, ana, 7.9, -72.5).status_code in (403, 409)


def test_dejar_de_compartir_borra_la_ubicacion(c):
    codigo, ana = en_camino(c)
    ubicar(c, codigo, ana, 7.9, -72.5)
    assert c.delete(f"/rescates/{codigo}/ubicacion", headers=sesion(c, LUIS)).status_code == 403
    assert c.delete(f"/rescates/{codigo}/ubicacion", headers=ana).status_code == 200
    assert mapa(c, codigo)["ubicacion"] is None


# --- Recorrido de demostración --------------------------------------------------------------

def test_la_simulacion_es_solo_para_cuentas_de_demostracion(c):
    codigo, ana = en_camino(c)
    assert c.post(f"/rescates/{codigo}/simulacion", headers=ana).status_code == 403
    assert mapa(c, codigo)["ubicacion"] is None


def test_la_simulacion_mueve_al_rescatista_hasta_el_animal_y_atiende(c, monkeypatch):
    monkeypatch.setattr(config, "SIMULACION_SEGUNDOS", 0.2)
    monkeypatch.setattr(config, "SIMULACION_INTERVALO_S", 0.02)
    monkeypatch.setattr(config, "SIMULACION_ESPERA_LLEGADA_S", 0.3)
    codigo, demo = en_camino(c, DEMO)
    respuesta = c.post(f"/rescates/{codigo}/simulacion", headers=demo)
    assert respuesta.status_code == 202
    distancias = []
    for _ in range(100):
        datos = mapa(c, codigo)
        if datos is None:
            break
        if datos["distancia_m"] is not None:
            assert datos["simulada"] is True and datos["nombre"] == "Rita"
            distancias.append(datos["distancia_m"])
        time.sleep(0.02)
    assert distancias and distancias[0] <= 1510 and min(distancias) < LLEGANDO_M
    pasos = c.get(f"/reportes/{codigo}/seguimiento").json()["pasos"]
    assert pasos[3]["nombre"] == "Atendido · Atendido en el sitio"
    assert c.app.state.demo_servicios[2]._rescates.ubicacion(codigo) is None
