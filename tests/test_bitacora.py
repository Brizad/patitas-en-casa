"""RF-32, RNF-12 (#102): bitácora general inmutable, sin cuerpos ni datos personales."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.bitacora.repositorio import Evento, RepositorioBitacoraEnMemoria
from app.bitacora.repositorio_postgres import RepositorioBitacoraPostgres
from tests.test_decision_adopcion import CLAVE, en_memoria, h


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioBitacoraPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioBitacoraEnMemoria()


def test_contrato_registra_y_devuelve_el_mas_reciente_primero(repositorio):
    for i in range(3):
        repositorio.registrar(Evento("coord@patitas.co", f"POST /x/{i}", {"id": str(i)}, 201))
    assert [e.accion for e in repositorio.recientes(2)] == ["POST /x/2", "POST /x/1"]
    assert repositorio.recientes()[0].objeto == {"id": "2"}


@pytest.mark.postgres
@pytest.mark.parametrize("sentencia", ["UPDATE bitacora SET actor = 'otro'",
                                       "DELETE FROM bitacora"])
def test_la_base_rechaza_editar_o_borrar(bd_limpia, sentencia):
    RepositorioBitacoraPostgres(bd_limpia).registrar(Evento("a@b.co", "POST /x", {}, 201))
    with pytest.raises(DBAPIError, match="inmutable"), bd_limpia.begin() as conexion:
        conexion.execute(text(sentencia))


def test_la_api_registra_los_cambios_con_actor_y_ruta_sin_el_cuerpo():
    c = en_memoria()
    coord = h(c, "coord@patitas.co")
    c.post("/refugio/ingresos", json={"nombre": "Canela", "especie": "gato",
                                      "estado_salud": "desnutrición leve"}, headers=coord)
    c.post("/refugio/animales/1/egreso", json={"motivo": "traslado"}, headers=coord)
    c.post("/adoptantes", json={"correo": "lau@correo.co", "nombre": "Laura",
                                "contrasena": CLAVE, "autoriza_datos": True})
    c.get("/refugio/animales", headers=coord)  # una lectura no se registra
    c.post("/refugio/ingresos", json={"nombre": "x"}, headers=coord)  # 422: no cambió nada
    # Los inicios de sesión también quedan (RF-16), pero aquí se miran los cambios de datos.
    eventos = [e for e in c.app.state.bitacora.recientes() if e.accion != "inicio de sesión"]
    assert [(e.actor, e.accion) for e in reversed(eventos)] == [
        ("coord@patitas.co", "POST /refugio/ingresos"),
        ("coord@patitas.co", "POST /refugio/animales/{animal_id}/egreso"),
        ("anónimo", "POST /adoptantes")]
    assert eventos[1].objeto == {"animal_id": "1"}
    texto = repr(eventos)
    assert CLAVE not in texto and "desnutrición" not in texto and "lau@correo.co" not in texto


def test_solo_el_administrador_lee_la_bitacora():
    c = en_memoria()
    assert c.get("/bitacora").status_code == 401
    assert c.get("/bitacora", headers=h(c, "coord@patitas.co")).status_code == 403
