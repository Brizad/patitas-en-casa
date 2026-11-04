"""Modo piloto de usabilidad (RNF-06, #258)."""
from datetime import UTC, datetime, timedelta

import pytest

from app.piloto.repositorio_postgres import RepositorioPilotoPostgres
from app.piloto.servicio import RepositorioPilotoEnMemoria, ServicioPiloto, puntaje_sus
from scripts.operacion.resultados_piloto import calcular
from tests.test_api import sesion

TEXTO = "Perro atropellado frente al parque Santander, no se levanta y sangra"
REPORTE = {"descripcion": TEXTO, "direccion": "Parque Santander, Cúcuta"}
SUS = [4, 2, 5, 1, 4, 2, 5, 1, 4, 2]  # SUS = 85


def cliente_con_admin():
    """El cliente de test_api más una cuenta de administración."""
    from fastapi.testclient import TestClient

    from app.api.main import crear_app
    from app.cupos.repositorio import RepositorioCuposEnMemoria
    from app.dominio.modelos import Refugio, Rol
    from app.reportes.repositorio import RepositorioEnMemoria
    from app.seguridad.tokens import EmisorTokens
    from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
    from app.usuarios.servicio import ServicioUsuarios
    from tests.test_api import CLAVE, SECRETO_PRUEBAS
    usuarios = RepositorioUsuariosEnMemoria()
    for correo, rol in (("vet@patitas.co", Rol.VETERINARIO), ("admin@patitas.co",
                                                              Rol.ADMINISTRADOR)):
        ServicioUsuarios(usuarios).registrar(correo, correo, rol, CLAVE)
    return TestClient(crear_app(RepositorioEnMemoria(),
                                RepositorioCuposEnMemoria(Refugio("R", capacidad=5)),
                                repositorio_usuarios=usuarios,
                                emisor_tokens=EmisorTokens(SECRETO_PRUEBAS)))


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioPilotoPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioPilotoEnMemoria()


def test_flujo_completo_participante_anonimo_reporta_y_responde(repositorio):
    servicio = ServicioPiloto(repositorio)
    p1, token = servicio.invitar()
    p2, _ = servicio.invitar()
    assert (p1.codigo, p2.codigo) == ("P01", "P02")
    from app.dominio.modelos import Ubicacion
    codigo = servicio.reportar(token, TEXTO, Ubicacion(direccion="Calle 10"))
    assert len(codigo) == 8
    servicio.responder(token, 62, SUS)
    assert [p.codigo for p in servicio.completos()] == ["P01"]
    assert servicio.invitados() == 2
    assert repositorio.todos()[0].sus == SUS and repositorio.todos()[0].segundos == 62


def test_el_csv_lo_lee_el_script_del_piloto():
    servicio = ServicioPiloto(RepositorioPilotoEnMemoria())
    from app.dominio.modelos import Ubicacion
    for segundos in (62, 120):
        _, token = servicio.invitar()
        servicio.reportar(token, TEXTO, Ubicacion(direccion="Calle 10"))
        servicio.responder(token, segundos, SUS)
    resultado = calcular(servicio.csv())
    assert (resultado.participantes, resultado.cumplen_tiempo) == (2, 1)
    assert resultado.sus_promedio == puntaje_sus(SUS) == 85


def test_token_vencido_usado_o_falso_se_rechaza():
    ahora = [datetime(2026, 11, 5, tzinfo=UTC)]
    servicio = ServicioPiloto(RepositorioPilotoEnMemoria(), reloj=lambda: ahora[0])
    from app.dominio.modelos import Ubicacion
    from app.piloto.servicio import PilotoRechazado
    _, token = servicio.invitar()
    with pytest.raises(PilotoRechazado, match="Primero envía"):
        servicio.responder(token, 30, SUS)
    servicio.reportar(token, TEXTO, Ubicacion(direccion="Calle 10"))
    servicio.responder(token, 30, SUS)
    with pytest.raises(PilotoRechazado) as usado:
        servicio.responder(token, 30, SUS)
    assert usado.value.estado_http == 409
    _, otro = servicio.invitar()
    ahora[0] += timedelta(hours=25)
    with pytest.raises(PilotoRechazado) as vencido:
        servicio.reportar(otro, TEXTO, Ubicacion(direccion="Calle 10"))
    assert vencido.value.estado_http == 403
    with pytest.raises(PilotoRechazado):
        servicio.reportar("token-inventado", TEXTO, Ubicacion(direccion="Calle 10"))


def test_api_el_reporte_de_piloto_no_llega_a_la_cola_y_el_csv_es_del_admin():
    c = cliente_con_admin()
    vet = sesion(c)
    assert c.post("/admin/piloto/participantes").status_code == 401
    assert c.post("/admin/piloto/participantes", headers=vet).status_code == 403
    admin = sesion(c, "admin@patitas.co")
    invitacion = c.post("/admin/piloto/participantes", headers=admin).json()
    assert invitacion["participante"] == "P01"
    assert invitacion["enlace"] == f"/app/?piloto={invitacion['token']}#reportar"
    piloto = {"X-Piloto": invitacion["token"]}
    sin_sentido = {**REPORTE, "descripcion": "Jsjsisoslqmwnabsnsnans Eksowpwpwowowowlwkksksks"}
    assert c.post("/piloto/reportes", json=sin_sentido, headers=piloto).status_code == 422
    r = c.post("/piloto/reportes", json=REPORTE, headers=piloto)
    assert r.status_code == 201 and r.json()["estado"] == "piloto"
    assert c.get("/cola", headers=vet).json() == []  # nunca entra a la cola
    assert c.get(f"/reportes/{r.json()['codigo']}").status_code == 404
    assert c.post("/piloto/resultados", json={"segundos": 62, "respuestas": SUS},
                  headers=piloto).status_code == 201
    assert c.post("/piloto/resultados", json={"segundos": 62, "respuestas": SUS},
                  headers=piloto).status_code == 409
    assert c.get("/admin/piloto/resultados", headers=admin).json() == {
        "invitados": 1, "completos": 1,
        "filas": [{"participante": "P01", "segundos": 62, "sus": 85.0}]}
    csv = c.get("/admin/piloto/resultados.csv", headers=admin)
    assert csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[1] == "P01,62,4,2,5,1,4,2,5,1,4,2"
    assert c.get("/admin/piloto/resultados.csv", headers=vet).status_code == 403


def test_api_sin_token_o_con_respuestas_incompletas():
    c = cliente_con_admin()
    assert c.post("/piloto/reportes", json=REPORTE).status_code == 403
    admin = sesion(c, "admin@patitas.co")
    token = c.post("/admin/piloto/participantes", headers=admin).json()["token"]
    c.post("/piloto/reportes", json=REPORTE, headers={"X-Piloto": token})
    r = c.post("/piloto/resultados", json={"segundos": 10, "respuestas": [3] * 9},
               headers={"X-Piloto": token})
    assert r.status_code == 422
