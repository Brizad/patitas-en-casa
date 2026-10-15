"""HU-02: el veterinario confirma o ajusta la prioridad sugerida (RF-04, RN-06, RN-16).

Comportamiento tomado del prototipo (docs/prototipo/interaccion.js, confirmarCon y
guardarajuste): solo se confirma un reporte pendiente; "Confirmar" acepta la sugerida (alta si
el clasificador no respondió); "Ajustar" exige justificación de 10 caracteres o más y queda en
la bitácora; la cola del veterinario muestra solo los pendientes.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import EstadoReporte, Prioridad, Refugio, Reporte, Rol, Ubicacion, Usuario
from app.reportes.confirmacion import (
    AjusteSinJustificacion,
    ReporteNoEncontrado,
    ReporteYaConfirmado,
    ServicioConfirmacion,
)
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

VET = Usuario("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, hash_contrasena="x")
COORD = Usuario("coord@patitas.co", "Coord", Rol.COORDINADOR, hash_contrasena="x")
CLAVE = "clave-de-prueba-larga"  # falsa
JUSTIFICACION = "En el video camina sin dificultad"


def reporte(codigo="ABCD1234", prioridad=Prioridad.MEDIA, estado=EstadoReporte.CLASIFICADO):
    return Reporte(codigo=codigo, descripcion="Perro con una herida en la pata trasera",
                   ubicacion=Ubicacion(direccion="Calle 10"), prioridad=prioridad,
                   confianza=0.7, estado=estado)


def servicio_con(*reportes):
    repositorio = RepositorioEnMemoria()
    for r in reportes:
        repositorio.guardar(r)
    return ServicioConfirmacion(repositorio), repositorio


# --- Servicio ---------------------------------------------------------------

def test_confirmar_acepta_la_prioridad_sugerida():
    servicio, repositorio = servicio_con(reporte())
    decision = servicio.confirmar("ABCD1234", VET)
    guardado = repositorio.buscar("ABCD1234")
    assert (guardado.estado, guardado.prioridad) == (EstadoReporte.CONFIRMADO, Prioridad.MEDIA)
    assert not decision.ajustada and decision.justificacion is None


def test_ajustar_con_justificacion_cambia_la_prioridad_y_queda_en_la_bitacora():
    servicio, repositorio = servicio_con(reporte())
    servicio.confirmar("ABCD1234", VET, Prioridad.BAJA, f"  {JUSTIFICACION}  ")
    assert repositorio.buscar("ABCD1234").prioridad == Prioridad.BAJA
    (decision,) = repositorio.decisiones("ABCD1234")
    assert (decision.veterinario, decision.prioridad_sugerida, decision.prioridad_final,
            decision.justificacion) == ("vet@patitas.co", Prioridad.MEDIA, Prioridad.BAJA,
                                        JUSTIFICACION)
    assert decision.ajustada


@pytest.mark.parametrize("justificacion", [None, "", "   ", "corta 9 c"])
def test_ajustar_sin_justificacion_suficiente_se_rechaza_y_nada_cambia(justificacion):
    """RN-16: cambiar la prioridad exige al menos 10 caracteres de justificación."""
    servicio, repositorio = servicio_con(reporte())
    with pytest.raises(AjusteSinJustificacion, match="10"):
        servicio.confirmar("ABCD1234", VET, Prioridad.CRITICA, justificacion)
    assert repositorio.buscar("ABCD1234").estado == EstadoReporte.CLASIFICADO
    assert repositorio.decisiones("ABCD1234") == []


def test_elegir_la_misma_prioridad_no_exige_justificacion():
    servicio, _ = servicio_con(reporte())
    assert not servicio.confirmar("ABCD1234", VET, Prioridad.MEDIA).ajustada


def test_reporte_sin_clasificar_se_confirma_como_alta():
    """RN-03: sin clasificación la sugerida es alta (falla segura)."""
    servicio, repositorio = servicio_con(reporte(prioridad=Prioridad.ALTA,
                                                 estado=EstadoReporte.SIN_CLASIFICAR))
    servicio.confirmar("ABCD1234", VET)
    assert repositorio.buscar("ABCD1234").prioridad == Prioridad.ALTA


def test_un_reporte_confirmado_no_se_vuelve_a_confirmar():
    servicio, _ = servicio_con(reporte())
    servicio.confirmar("ABCD1234", VET)
    with pytest.raises(ReporteYaConfirmado):
        servicio.confirmar("ABCD1234", VET, Prioridad.CRITICA, JUSTIFICACION)


def test_codigo_inexistente():
    servicio, _ = servicio_con()
    with pytest.raises(ReporteNoEncontrado):
        servicio.confirmar("NOEXISTE", VET)


def test_solo_el_veterinario_confirma():
    """RN-06, también dentro del servicio (no solo en la API)."""
    servicio, _ = servicio_con(reporte())
    with pytest.raises(PermissionError):
        servicio.confirmar("ABCD1234", COORD)


# --- API --------------------------------------------------------------------

def cliente():
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    app = crear_app(RepositorioEnMemoria(),
                    RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
                    repositorio_usuarios=usuarios,
                    emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres"))
    return TestClient(app)


def sesion(c, correo="vet@patitas.co"):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def nuevo_reporte(c, descripcion="Perro atropellado en la avenida, está sangrando mucho"):
    return c.post("/reportes", json={"descripcion": descripcion,
                                     "direccion": "Calle 10 # 5-30"}).json()["codigo"]


def test_api_confirmar_y_la_cola_ya_no_lo_muestra():
    c = cliente()
    codigo = nuevo_reporte(c)
    vet = sesion(c)
    respuesta = c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=vet)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"codigo": codigo, "estado": "confirmado",
                                "prioridad": "critica", "ajustada": False}
    assert c.get("/cola", headers=vet).json() == []


def test_api_ajuste_sin_justificacion_da_422():
    c = cliente()
    codigo = nuevo_reporte(c)
    respuesta = c.post(f"/reportes/{codigo}/confirmacion", json={"prioridad": "baja"},
                       headers=sesion(c))
    assert respuesta.status_code == 422
    assert "10 caracteres" in respuesta.json()["detail"]


def test_api_ajuste_con_justificacion_y_bitacora():
    c = cliente()
    codigo = nuevo_reporte(c)
    vet = sesion(c)
    c.post(f"/reportes/{codigo}/confirmacion",
           json={"prioridad": "alta", "justificacion": JUSTIFICACION}, headers=vet)
    bitacora = c.get(f"/reportes/{codigo}/decisiones", headers=sesion(c, "coord@patitas.co"))
    assert bitacora.status_code == 200
    (decision,) = bitacora.json()
    assert {k: decision[k] for k in ("veterinario", "prioridad_sugerida", "prioridad_final",
                                     "justificacion")} == {
        "veterinario": "vet@patitas.co", "prioridad_sugerida": "critica",
        "prioridad_final": "alta", "justificacion": JUSTIFICACION}


def test_api_segunda_confirmacion_da_409_y_codigo_inexistente_404():
    c = cliente()
    codigo = nuevo_reporte(c)
    vet = sesion(c)
    c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=vet)
    assert c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=vet).status_code == 409
    assert c.post("/reportes/NOEXISTE/confirmacion", json={}, headers=vet).status_code == 404


def test_api_el_codigo_se_acepta_en_minusculas():
    c = cliente()
    codigo = nuevo_reporte(c)
    respuesta = c.post(f"/reportes/{codigo.lower()}/confirmacion", json={}, headers=sesion(c))
    assert respuesta.status_code == 200


def test_api_coordinador_no_confirma_y_sin_sesion_401():
    """RN-06: solo el veterinario confirma."""
    c = cliente()
    codigo = nuevo_reporte(c)
    ruta = f"/reportes/{codigo}/confirmacion"
    assert c.post(ruta, json={}, headers=sesion(c, "coord@patitas.co")).status_code == 403
    assert c.post(ruta, json={}).status_code == 401
    assert c.get(f"/reportes/{codigo}/decisiones").status_code == 401


def test_api_prioridad_desconocida_da_422():
    c = cliente()
    codigo = nuevo_reporte(c)
    respuesta = c.post(f"/reportes/{codigo}/confirmacion",
                       json={"prioridad": "urgentisima", "justificacion": JUSTIFICACION},
                       headers=sesion(c))
    assert respuesta.status_code == 422
