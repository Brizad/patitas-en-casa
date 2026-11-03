"""Avisos al ciudadano por el outbox: rescatado e ingreso al refugio (RF-18, RN-14)."""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.avisos.modelos import AvisoNuevo
from app.avisos.repositorio import RepositorioAvisosEnMemoria
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.cifrado import Cifrador
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
CLAVE_DATOS = "clave-de-datos-de-pruebas-con-mas-de-32-caracteres"  # falsa
DIRECCION = "Calle 8 con Av. 4 frente a la panadería"
REPORTE = {"descripcion": "Perro atropellado en la avenida, está sangrando mucho",
           "direccion": DIRECCION, "latitud": 7.8939, "longitud": -72.5078}
FICHA = {"nombre": "Firulais", "especie": "perro", "estado_salud": "Estable"}
PALABRAS_PROHIBIDAS = ("perro", "atropellado", "sangrando", "panadería", "calle", "crítica",
                       "critica", "alta", "prioridad", "firulais", "ana@rescate.co")


class Espia:
    def __init__(self):
        self.enviados = []

    def entregar(self, destinatario, mensaje):
        self.enviados.append((destinatario, mensaje))


@pytest.fixture
def entorno():
    usuarios = RepositorioUsuariosEnMemoria()
    for correo, rol in [("vet@patitas.co", Rol.VETERINARIO), ("ana@rescate.co", Rol.RESCATISTA),
                        ("coord@patitas.co", Rol.COORDINADOR)]:
        ServicioUsuarios(usuarios).registrar(correo, "Persona", rol, CLAVE)
    espia = Espia()
    repo = RepositorioEnMemoria()
    c = TestClient(crear_app(
        repo, RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
        repositorio_usuarios=usuarios, notificador=espia, cifrador=Cifrador(CLAVE_DATOS),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))
    return c, repo, espia


def sesion(c, correo):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def reportar(c, contacto="lau@correo.co"):
    cuerpo = dict(REPORTE)
    if contacto:
        cuerpo.update(contacto=contacto, autoriza_contacto=True)
    return c.post("/reportes", json=cuerpo).json()["codigo"]


def rescatar(c, codigo, resultado="trasladado"):
    """Confirma, el rescatista acepta, llega y registra el resultado."""
    c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=sesion(c, "vet@patitas.co"))
    ana = sesion(c, "ana@rescate.co")
    c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=ana)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    c.post(f"/rescates/{codigo}/llegue", headers=ana)
    return c.post(f"/rescates/{codigo}/resultado", json={"resultado": resultado}, headers=ana)


def al_ciudadano(c, espia):
    c.app.state.procesador_avisos.procesar()
    return [m for d, m in espia.enviados if d == "lau@correo.co"]


@pytest.mark.parametrize("resultado", ["trasladado", "atendido_en_sitio"])
def test_al_quedar_rescatado_el_ciudadano_recibe_un_aviso(entorno, resultado):
    c, repo, espia = entorno
    codigo = reportar(c)
    assert rescatar(c, codigo, resultado).status_code == 200
    mensajes = al_ciudadano(c, espia)
    assert len(mensajes) == 2  # «lo revisó el veterinario» y «rescatado»
    rescatado = [m for m in mensajes if "rescat" in m.lower() and "revisó" not in m]
    assert rescatado and codigo in rescatado[0]


@pytest.mark.parametrize("resultado", ["no_encontrado", "fallecido"])
def test_sin_rescate_no_se_avisa_que_fue_rescatado(entorno, resultado):
    c, repo, espia = entorno
    codigo = reportar(c)
    rescatar(c, codigo, resultado)
    assert len(al_ciudadano(c, espia)) == 1  # solo el de la revisión


def test_sin_correo_o_con_telefono_no_hay_aviso(entorno):
    c, repo, espia = entorno
    sin_contacto = reportar(c, contacto=None)
    con_telefono = reportar(c, contacto="300 123 4567")
    for codigo in (sin_contacto, con_telefono):
        rescatar(c, codigo)
        assert [a for a in repo.avisos.de_reporte(codigo)
                if a.destinatario.startswith("cifrado:")] == []


def test_el_aviso_de_rescatado_no_lleva_datos_sensibles(entorno):
    c, repo, espia = entorno
    codigo = reportar(c)
    rescatar(c, codigo)
    for aviso in repo.avisos.de_reporte(codigo):
        if aviso.destinatario.startswith("cifrado:"):
            assert "lau" not in aviso.destinatario  # va cifrado también en la tabla
            minusculas = aviso.mensaje.lower()
            assert not [p for p in PALABRAS_PROHIBIDAS if p in minusculas], aviso.mensaje


def test_al_ingresar_al_refugio_el_ciudadano_recibe_un_aviso(entorno):
    c, repo, espia = entorno
    codigo = reportar(c)
    r = c.post("/refugio/ingresos", json={**FICHA, "reporte": codigo},
               headers=sesion(c, "coord@patitas.co"))
    assert r.status_code == 201
    mensajes = al_ciudadano(c, espia)
    assert len(mensajes) == 1 and codigo in mensajes[0] and "refugio" in mensajes[0].lower()
    minusculas = mensajes[0].lower()
    assert not [p for p in PALABRAS_PROHIBIDAS if p in minusculas], mensajes[0]


def test_ingreso_sin_reporte_funciona_como_antes(entorno):
    c, repo, espia = entorno
    r = c.post("/refugio/ingresos", json=FICHA, headers=sesion(c, "coord@patitas.co"))
    assert r.status_code == 201 and al_ciudadano(c, espia) == []


def test_ingreso_con_reporte_inexistente_se_rechaza_sin_ingresar(entorno):
    c, repo, espia = entorno
    cabeceras = sesion(c, "coord@patitas.co")
    r = c.post("/refugio/ingresos", json={**FICHA, "reporte": "NOEXISTE"}, headers=cabeceras)
    assert r.status_code == 422
    assert c.get("/refugio/ocupacion", headers=cabeceras).json()["porcentaje"] == 0


def test_ingresar_dos_veces_el_mismo_reporte_avisa_una_sola_vez(entorno):
    c, repo, espia = entorno
    codigo = reportar(c)
    cabeceras = sesion(c, "coord@patitas.co")
    for _ in range(2):
        c.post("/refugio/ingresos", json={**FICHA, "reporte": codigo}, headers=cabeceras)
    assert len(al_ciudadano(c, espia)) == 1


def test_el_outbox_distingue_avisos_distintos_al_mismo_destinatario():
    repo, ahora = RepositorioAvisosEnMemoria(), datetime.now(UTC)
    assert repo.agregar("ABC12345", [AvisoNuevo("x", "uno"), AvisoNuevo("x", "dos")], ahora) == 2
    assert repo.agregar("ABC12345", [AvisoNuevo("x", "uno")], ahora) == 0  # repetido

