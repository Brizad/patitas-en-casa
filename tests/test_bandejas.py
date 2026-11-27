"""#496: regla única de orden de las bandejas, «Atrasados», archivar y la cola del ciudadano."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Prioridad, Refugio, Rol
from app.reportes import orden
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
CRITICO = "Perro atropellado en la avenida, está sangrando mucho"
LEVE = "Gata con sarna en el andén del barrio, se ve tranquila"
MOTIVO = "Nadie contestó y no se encontró el lugar"


@pytest.fixture
def entorno():
    usuarios = RepositorioUsuariosEnMemoria()
    for correo, rol in [("vet@patitas.co", Rol.VETERINARIO), ("ana@rescate.co", Rol.RESCATISTA)]:
        ServicioUsuarios(usuarios).registrar(correo, "Persona", rol, CLAVE)
    repositorio = RepositorioEnMemoria()
    c = TestClient(crear_app(
        repositorio, RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))
    return c, repositorio


def sesion(c, correo="vet@patitas.co"):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def reportar(entorno, texto=CRITICO, horas=0.0):
    """Reporte creado hace `horas` horas (se cambia la fecha en el repositorio en memoria)."""
    c, repositorio = entorno
    codigo = c.post("/reportes", json={"descripcion": texto, "direccion": "Calle 10",
                                       "latitud": 7.8939, "longitud": -72.5078}).json()["codigo"]
    repositorio.buscar(codigo).creado_en = datetime.now(UTC) - timedelta(hours=horas)
    return codigo


def cola(c):
    return c.get("/cola", headers=sesion(c)).json()


# --- La regla ---------------------------------------------------------------------------

def test_niveles_urgente_alta_y_normal():
    assert [orden.nivel(p) for p in Prioridad] == ["urgente", "alta", "normal", "normal"]
    assert orden.nivel(None) == "normal"


def test_orden_por_nivel_y_luego_el_mas_antiguo(entorno):
    c, _ = entorno
    leve_viejo = reportar(entorno, LEVE, horas=5)
    critico_nuevo = reportar(entorno, CRITICO, horas=0.1)
    critico_viejo = reportar(entorno, CRITICO, horas=2)
    leve_nuevo = reportar(entorno, LEVE, horas=1)
    assert [r["codigo"] for r in cola(c)] == [critico_viejo, critico_nuevo, leve_viejo, leve_nuevo]


def test_mas_de_72_horas_va_en_atrasados_y_no_en_la_principal(entorno):
    c, _ = entorno
    reciente = reportar(entorno, horas=71)
    viejo = reportar(entorno, horas=73)
    filas = {r["codigo"]: r for r in cola(c)}
    assert (filas[reciente]["atrasado"], filas[viejo]["atrasado"]) == (False, True)
    # La principal (lo que no está atrasado) no lo trae, aunque sea el más antiguo.
    assert [r["codigo"] for r in cola(c) if not r["atrasado"]] == [reciente]


def test_la_tarjeta_trae_animal_y_estado_solo_si_el_reporte_los_dice(entorno):
    c, _ = entorno
    reportar(entorno, CRITICO)
    reportar(entorno, "Animal tirado en la vía, no se mueve y nadie lo recoge", horas=1)
    filas = cola(c)
    por_texto = {r["descripcion"]: r for r in filas}
    assert por_texto[CRITICO]["especie"] == "perro"
    assert por_texto[CRITICO]["estado_animal"] == "atropellado"
    assert por_texto["Animal tirado en la vía, no se mueve y nadie lo recoge"]["especie"] is None
    assert orden.especie_mencionada("un gatito y un perro") == "gato"


# --- Archivar -----------------------------------------------------------------------------

def archivar(c, codigo, justificacion=MOTIVO):
    return c.post(f"/reportes/{codigo}/descarte", headers=sesion(c),
                  json={"motivo": "archivado", "justificacion": justificacion})


def test_archivar_exige_motivo_y_solo_atrasados(entorno):
    c, _ = entorno
    viejo = reportar(entorno, horas=80)
    assert archivar(c, viejo, justificacion="").status_code == 422
    assert archivar(c, viejo, justificacion="..........").status_code == 422
    assert archivar(c, reportar(entorno, horas=1)).status_code == 422  # no está atrasado
    assert archivar(c, viejo).status_code == 200
    assert viejo not in [r["codigo"] for r in cola(c)]  # sale de la cola


def test_archivar_queda_en_el_historial_y_el_ciudadano_lo_ve_cerrado(entorno):
    c, repositorio = entorno
    viejo = reportar(entorno, horas=80)
    archivar(c, viejo)
    descarte = repositorio.descarte(viejo)
    assert (descarte.motivo.value, descarte.justificacion) == ("archivado", MOTIVO)
    historial = c.get("/veterinario/historial", headers=sesion(c)).json()
    assert [(h["codigo"], h["accion"]) for h in historial] == [(viejo, "archivado")]
    pasos = c.get(f"/reportes/{viejo}/seguimiento").json()["pasos"]
    assert [(p["nombre"], p["detalle"]) for p in pasos] == [
        ("Recibido", None), ("Cerrado", "No pudimos verificar el reporte")]
    assert MOTIVO not in str(pasos)  # el ciudadano no ve la nota del veterinario


def test_solo_el_veterinario_archiva(entorno):
    c, _ = entorno
    viejo = reportar(entorno, horas=80)
    respuesta = c.post(f"/reportes/{viejo}/descarte", headers=sesion(c, "ana@rescate.co"),
                       json={"motivo": "archivado", "justificacion": MOTIVO})
    assert respuesta.status_code == 403


# --- Ciudadano ------------------------------------------------------------------------

def test_posicion_en_la_cola_con_la_misma_regla_sin_atrasados(entorno):
    c, _ = entorno
    reportar(entorno, CRITICO, horas=100)  # atrasado: no cuenta
    reportar(entorno, CRITICO, horas=3)
    reportar(entorno, LEVE, horas=5)  # normal, más viejo que el mío: igual va después
    mio = reportar(entorno, CRITICO, horas=1)
    assert c.get(f"/reportes/{mio}/seguimiento").json()["cola"] == {"antes": 1}
    primero = reportar(entorno, CRITICO, horas=4)
    assert c.get(f"/reportes/{primero}/seguimiento").json()["cola"] == {"antes": 0}


def test_el_nivel_se_ve_solo_despues_del_triaje(entorno):
    c, _ = entorno
    codigo = reportar(entorno, LEVE)
    antes = c.get(f"/reportes/{codigo}/seguimiento").json()
    assert "nivel" not in antes and "cola" in antes
    c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=sesion(c))
    despues = c.get(f"/reportes/{codigo}/seguimiento").json()
    assert despues["nivel"] == "normal" and "cola" not in despues


def test_cada_paso_hecho_trae_su_hora_real(entorno):
    c, repositorio = entorno
    codigo = reportar(entorno, CRITICO)
    c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=sesion(c))
    pasos = c.get(f"/reportes/{codigo}/seguimiento").json()["pasos"]
    creado = repositorio.buscar(codigo).creado_en
    decidido = repositorio.decisiones(codigo)[-1].decidido_en
    assert datetime.fromisoformat(pasos[0]["fecha"]) == creado
    assert datetime.fromisoformat(pasos[1]["fecha"]) == decidido
    assert all(p["fecha"] is None for p in pasos if p["estado"] != "hecho")


# --- Rescatista ---------------------------------------------------------------------------

def test_ofertas_en_el_orden_unico_y_atrasadas_marcadas(entorno):
    c, repositorio = entorno
    vet = sesion(c)
    alto = reportar(entorno, LEVE, horas=2)
    critico = reportar(entorno, CRITICO, horas=1)
    viejo = reportar(entorno, CRITICO, horas=90)
    for codigo, prioridad in [(alto, "alta"), (critico, None), (viejo, None)]:
        cuerpo = {"prioridad": prioridad, "justificacion": "Se ve grave en la descripción"} \
            if prioridad else {}
        c.post(f"/reportes/{codigo}/confirmacion", json=cuerpo, headers=vet)
    repositorio.decisiones(viejo)[-1].decidido_en = datetime.now(UTC) - timedelta(hours=80)
    ana = sesion(c, "ana@rescate.co")
    c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=ana)
    ofertas = c.get("/rescates/ofertas", headers=ana).json()
    assert [(o["codigo"], o["atrasado"]) for o in ofertas] == [
        (viejo, True), (critico, False), (alto, False)]
    assert ofertas[0]["nivel"] == "urgente" and ofertas[2]["nivel"] == "alta"
