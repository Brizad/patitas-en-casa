"""HU-06, parte 2: zona por comunas, alerta por correo y escalamiento (#57, decisión de #46).

Respaldo en el prototipo (docs/prototipo/index.html): "Escalamiento sin aceptar (crítico /
alto): 15 / 30 min · RF-23", "Zona: Comuna 6 y alrededores" y "Si nadie acepta en 15 min, se
amplía el radio" (con comunas, se amplía a toda la ciudad).
"""
import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import (
    DecisionTriaje,
    EstadoReporte,
    Prioridad,
    Refugio,
    Reporte,
    Rol,
    Ubicacion,
    Usuario,
)
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.rescates.escalamiento import vigilar_escalamientos
from app.rescates.repositorio import RepositorioRescatesEnMemoria
from app.rescates.repositorio_postgres import RepositorioRescatesPostgres
from app.rescates.servicio import ServicioRescates
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

INICIO = datetime(2026, 10, 15, 8, 0, tzinfo=UTC)
ANA, LUIS, EVA = "ana@rescate.co", "luis@rescate.co", "eva@rescate.co"
CLAVE = "clave-de-prueba-larga"  # falsa
CRITICO = "Perro atropellado en la avenida, está sangrando mucho"
LEVE = "Gato con sarna en el andén del barrio, se ve tranquilo"


class Reloj:
    def __init__(self) -> None:
        self.ahora = INICIO

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **tiempo) -> None:
        self.ahora += timedelta(**tiempo)


class NotificadorFalso:
    def __init__(self) -> None:
        self.enviados: list[tuple[str, str]] = []

    def enviar(self, destinatario: str, mensaje: str) -> None:
        self.enviados.append((destinatario, mensaje))

    def para(self, destinatario: str) -> list[str]:
        return [m for d, m in self.enviados if d == destinatario]


def rescatista(correo: str) -> Usuario:
    return Usuario(correo, correo.split("@")[0], Rol.RESCATISTA, hash_contrasena="x")


# --- Contrato del repositorio ----------------------------------------------

@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        motor = request.getfixturevalue("bd_limpia")
        RepositorioPostgres(motor).guardar(Reporte(
            codigo="AAAA0001", descripcion=CRITICO, ubicacion=Ubicacion(direccion="Calle 10"),
            estado=EstadoReporte.CONFIRMADO, prioridad=Prioridad.CRITICA))
        return RepositorioRescatesPostgres(motor)
    return RepositorioRescatesEnMemoria()


def test_sin_zona_definida_la_zona_es_vacia(repositorio):
    assert repositorio.zona(ANA) == frozenset()


def test_poner_zona_no_cambia_la_disponibilidad_ni_al_reves(repositorio):
    repositorio.poner_zona(ANA, frozenset({6, 7}))
    assert repositorio.esta_disponible(ANA) is False
    repositorio.poner_disponible(ANA, True)
    assert repositorio.zona(ANA) == frozenset({6, 7})
    repositorio.poner_zona(ANA, frozenset({2}))
    assert repositorio.esta_disponible(ANA) is True
    assert repositorio.zona(ANA) == frozenset({2})


def test_disponibles_devuelve_solo_los_disponibles_con_su_zona(repositorio):
    repositorio.poner_disponible(ANA, True)
    repositorio.poner_zona(ANA, frozenset({6}))
    repositorio.poner_disponible(LUIS, True)
    repositorio.poner_disponible(EVA, True)
    repositorio.poner_disponible(EVA, False)
    assert repositorio.disponibles() == {ANA: frozenset({6}), LUIS: frozenset()}


def test_escalar_solo_una_vez(repositorio):
    assert repositorio.escalados() == set()
    assert repositorio.marcar_escalado("AAAA0001", INICIO) is True
    assert repositorio.marcar_escalado("AAAA0001", INICIO + timedelta(minutes=1)) is False
    assert repositorio.escalados() == {"AAAA0001"}


@pytest.mark.postgres
@pytest.mark.parametrize("sentencia", [
    "UPDATE reportes SET comuna = 11",
    "UPDATE reportes SET comuna = 0",
    "INSERT INTO rescatistas (correo, comunas) VALUES ('x@r.co', '{6, 11}')",
])
def test_la_base_rechaza_comunas_fuera_de_cucuta(bd_limpia, sentencia):
    RepositorioPostgres(bd_limpia).guardar(Reporte(
        codigo="AAAA0001", descripcion=CRITICO, ubicacion=Ubicacion(direccion="Calle 10")))
    with pytest.raises(IntegrityError), bd_limpia.begin() as conexion:
        conexion.execute(text(sentencia))


@pytest.mark.postgres
def test_la_comuna_del_reporte_se_guarda_en_postgres(bd_limpia):
    repositorio = RepositorioPostgres(bd_limpia)
    repositorio.guardar(Reporte(codigo="AAAA0001", descripcion=CRITICO,
                                ubicacion=Ubicacion(direccion="Calle 10", comuna=6)))
    assert repositorio.buscar("AAAA0001").ubicacion.comuna == 6
    assert repositorio.todos()[0].ubicacion.comuna == 6


# --- Servicio ----------------------------------------------------------------

class Escenario:
    """Reportes y rescates en memoria, notificador falso y reloj manual."""

    def __init__(self) -> None:
        self.reloj = Reloj()
        self.reportes = RepositorioEnMemoria()
        self.rescates = RepositorioRescatesEnMemoria()
        self.notificador = NotificadorFalso()
        self.servicio = ServicioRescates(self.reportes, self.rescates,
                                         notificador=self.notificador, reloj=self.reloj)

    def confirmado(self, codigo: str, prioridad=Prioridad.CRITICA, comuna: int | None = 6):
        self.reportes.guardar(Reporte(codigo=codigo, descripcion=CRITICO,
                                      ubicacion=Ubicacion(direccion="Calle 8", comuna=comuna),
                                      estado=EstadoReporte.CLASIFICADO, prioridad=prioridad,
                                      creado_en=self.reloj()))
        self.reportes.confirmar(DecisionTriaje(codigo, "vet@patitas.co", prioridad, prioridad,
                                               decidido_en=self.reloj()))
        return self.reportes.buscar(codigo)

    def disponible(self, correo: str, *comunas: int) -> Usuario:
        self.rescates.poner_disponible(correo, True)
        self.rescates.poner_zona(correo, frozenset(comunas))
        return rescatista(correo)


@pytest.fixture
def e():
    return Escenario()


def codigos(reportes):
    return [r.codigo for r in reportes]


def test_ofertas_solo_de_la_zona_del_rescatista(e):
    e.confirmado("COMUNA06", comuna=6)
    e.confirmado("COMUNA02", comuna=2)
    assert codigos(e.servicio.ofertas(e.disponible(ANA, 6, 7))) == ["COMUNA06"]


def test_sin_zona_el_rescatista_ve_toda_la_ciudad(e):
    e.confirmado("COMUNA06", comuna=6)
    e.confirmado("COMUNA02", comuna=2)
    assert sorted(codigos(e.servicio.ofertas(e.disponible(ANA)))) == ["COMUNA02", "COMUNA06"]


def test_reporte_sin_comuna_se_ofrece_a_todos(e):
    e.confirmado("SINCOMUN", comuna=None)
    assert codigos(e.servicio.ofertas(e.disponible(ANA, 6))) == ["SINCOMUN"]


def test_al_confirmar_se_avisa_por_correo_a_los_disponibles_de_la_zona(e):
    e.disponible(ANA, 6)
    e.disponible(LUIS, 2)
    e.disponible(EVA)  # toda la ciudad
    e.rescates.poner_disponible("no@rescate.co", False)
    e.servicio.alertar_confirmado(e.confirmado("COMUNA06", comuna=6).codigo)
    assert sorted(d for d, _ in e.notificador.enviados) == [ANA, EVA]
    mensaje = e.notificador.para(ANA)[0]
    assert "COMUNA06" in mensaje and "comuna 6" in mensaje
    assert "Calle 8" not in mensaje  # la dirección exacta se entrega al aceptar


def test_no_se_avisa_a_quien_ya_tiene_un_rescate_activo(e):
    e.confirmado("PRIMERO1")
    ana = e.disponible(ANA, 6)
    e.servicio.aceptar(ana, "PRIMERO1")
    e.servicio.alertar_confirmado(e.confirmado("SEGUNDO2").codigo)
    assert e.notificador.enviados == []


@pytest.mark.parametrize("prioridad", [Prioridad.MEDIA, Prioridad.BAJA])
def test_media_y_baja_no_avisan_a_rescatistas(e, prioridad):
    e.disponible(ANA)
    e.servicio.alertar_confirmado(e.confirmado("LEVE0001", prioridad=prioridad).codigo)
    assert e.notificador.enviados == []


@pytest.mark.parametrize("prioridad, minutos", [(Prioridad.CRITICA, 15), (Prioridad.ALTA, 30)])
def test_sin_aceptar_se_escala_al_coordinador_una_sola_vez(e, prioridad, minutos):
    e.confirmado("ESPERA01", prioridad=prioridad)
    e.reloj.avanzar(minutes=minutos, seconds=-1)
    assert e.servicio.escalar_vencidos() == []
    e.reloj.avanzar(seconds=1)
    assert e.servicio.escalar_vencidos() == ["ESPERA01"]
    assert e.servicio.escalar_vencidos() == []
    avisos = e.notificador.para("coordinadores")
    assert len(avisos) == 1
    assert "ESPERA01" in avisos[0] and f"{minutos} min" in avisos[0]


def test_al_escalar_se_amplia_a_toda_la_ciudad(e):
    e.confirmado("COMUNA06", comuna=6)
    ana = e.disponible(ANA, 6)
    luis = e.disponible(LUIS, 2)
    assert e.servicio.ofertas(luis) == []
    e.reloj.avanzar(minutes=15)
    e.servicio.escalar_vencidos()
    assert codigos(e.servicio.ofertas(luis)) == ["COMUNA06"]
    assert len(e.notificador.para(LUIS)) == 1  # se le avisa ahora
    assert e.notificador.para(ANA) == []  # ya se le había avisado al confirmar
    assert codigos(e.servicio.ofertas(ana)) == ["COMUNA06"]


def test_un_rescate_aceptado_no_se_escala(e):
    e.confirmado("TOMADO01")
    e.servicio.aceptar(e.disponible(ANA, 6), "TOMADO01")
    e.reloj.avanzar(hours=1)
    assert e.servicio.escalar_vencidos() == []
    assert e.notificador.para("coordinadores") == []


def test_una_falla_del_correo_no_detiene_el_escalamiento(e):
    class CorreoRoto:
        def enviar(self, destinatario, mensaje):
            raise OSError("SMTP caído")

    servicio = ServicioRescates(e.reportes, e.rescates, notificador=CorreoRoto(), reloj=e.reloj)
    e.confirmado("ESPERA01")
    e.disponible(ANA)
    servicio.alertar_confirmado("ESPERA01")
    e.reloj.avanzar(minutes=15)
    assert servicio.escalar_vencidos() == ["ESPERA01"]


# --- Revisión periódica ------------------------------------------------------

def test_la_vigilancia_revisa_periodicamente_y_sobrevive_a_errores():
    llamadas = []

    def escalar():
        llamadas.append(1)
        if len(llamadas) == 1:
            raise RuntimeError("base caída un momento")

    async def correr():
        tarea = asyncio.create_task(vigilar_escalamientos(escalar, cada_s=0.01))
        while len(llamadas) < 3:
            await asyncio.sleep(0.01)
        tarea.cancel()

    asyncio.run(asyncio.wait_for(correr(), timeout=5))
    assert len(llamadas) >= 3


# --- API -----------------------------------------------------------------------

@pytest.fixture
def api():
    usuarios = RepositorioUsuariosEnMemoria()
    for correo, rol in [("vet@patitas.co", Rol.VETERINARIO), ("coord@patitas.co", Rol.COORDINADOR),
                        (ANA, Rol.RESCATISTA), (LUIS, Rol.RESCATISTA)]:
        ServicioUsuarios(usuarios).registrar(correo, correo.split("@")[0], rol, CLAVE)
    notificador = NotificadorFalso()
    c = TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
        repositorio_usuarios=usuarios, notificador=notificador,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))
    return c, notificador


def sesion(c, correo):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


@pytest.mark.parametrize("comuna", [0, 11])
def test_api_rechaza_comunas_fuera_de_cucuta(api, comuna):
    c, _ = api
    respuesta = c.post("/reportes", json={"descripcion": CRITICO, "direccion": "Calle 8",
                                          "comuna": comuna})
    assert respuesta.status_code == 422


def test_api_zona_del_rescatista(api):
    c, _ = api
    ana = sesion(c, ANA)
    respuesta = c.put("/rescatistas/yo/zona", json={"comunas": [7, 6, 6]}, headers=ana)
    assert respuesta.json() == {"comunas": [6, 7]}
    c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=ana)
    assert c.get("/rescatistas/yo", headers=ana).json() == {"disponible": True, "comunas": [6, 7]}


@pytest.mark.parametrize("comunas", [[0], [11], [6, 12]])
def test_api_zona_rechaza_comunas_invalidas(api, comunas):
    c, _ = api
    respuesta = c.put("/rescatistas/yo/zona", json={"comunas": comunas},
                      headers=sesion(c, ANA))
    assert respuesta.status_code == 422


@pytest.mark.parametrize("correo, esperado", [(None, 401), ("vet@patitas.co", 403),
                                              ("coord@patitas.co", 403)])
def test_api_zona_solo_para_rescatistas(api, correo, esperado):
    c, _ = api
    cabeceras = sesion(c, correo) if correo else {}
    assert c.put("/rescatistas/yo/zona", json={"comunas": [6]},
                 headers=cabeceras).status_code == esperado
    assert c.get("/rescatistas/yo", headers=cabeceras).status_code == esperado


def test_api_confirmar_un_critico_avisa_a_la_zona_y_la_oferta_muestra_la_comuna(api):
    c, notificador = api
    ana, luis = sesion(c, ANA), sesion(c, LUIS)
    for cabeceras, comuna in ((ana, 6), (luis, 2)):
        c.put("/rescatistas/yo/zona", json={"comunas": [comuna]}, headers=cabeceras)
        c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=cabeceras)
    codigo = c.post("/reportes", json={"descripcion": CRITICO, "direccion": "Calle 8",
                                       "comuna": 6}).json()["codigo"]
    confirmado = c.post(f"/reportes/{codigo}/confirmacion", json={},
                        headers=sesion(c, "vet@patitas.co"))
    assert confirmado.status_code == 200
    # #63: confirmar ya no envía; deja el aviso pendiente y el procesador lo envía después.
    assert confirmado.json()["avisos"] == {"programados": 1, "estado": "pendiente"}
    assert notificador.enviados == []
    c.app.state.procesador_avisos.procesar()
    assert [d for d, _ in notificador.enviados] == [ANA]
    ofertas = c.get("/rescates/ofertas", headers=ana).json()
    assert [(o["codigo"], o["comuna"], o["escalado"]) for o in ofertas] == [(codigo, 6, False)]
    assert c.get("/rescates/ofertas", headers=luis).json() == []
