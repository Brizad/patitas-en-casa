"""RNF-12 (#149): la bitácora guarda el valor anterior y el nuevo, sin datos personales."""
import pytest

from app.bitacora.repositorio import Evento
from app.bitacora.repositorio_postgres import RepositorioBitacoraPostgres
from tests.test_decision_adopcion import CLAVE, en_memoria, h


def ultimo(c, accion):
    return next(e for e in c.app.state.bitacora.recientes() if e.accion == accion)


@pytest.mark.postgres
def test_el_repositorio_guarda_y_devuelve_los_valores(bd_limpia):
    repo = RepositorioBitacoraPostgres(bd_limpia)
    repo.registrar(Evento("vet@patitas.co", "POST /x", {}, 200,
                          anterior={"prioridad": "media"}, nuevo={"prioridad": "alta"}))
    repo.registrar(Evento("anónimo", "POST /reportes", {}, 201))
    sin, con = repo.recientes(2)
    assert (sin.anterior, sin.nuevo) == (None, None)
    assert (con.anterior, con.nuevo) == ({"prioridad": "media"}, {"prioridad": "alta"})


def test_ingreso_y_egreso_guardan_la_ocupacion_de_antes_y_despues():
    c = en_memoria()
    coord = h(c, "coord@patitas.co")
    c.post("/refugio/ingresos", json={"nombre": "Canela", "especie": "gato",
                                      "estado_salud": "desnutrición leve"}, headers=coord)
    ingreso = ultimo(c, "POST /refugio/ingresos")
    assert ingreso.anterior["ocupacion"] != ingreso.nuevo["ocupacion"]
    c.post("/refugio/animales/1/egreso", json={"motivo": "traslado"}, headers=coord)
    egreso = ultimo(c, "POST /refugio/animales/{animal_id}/egreso")
    assert egreso.anterior["en_refugio"] is True
    assert egreso.nuevo == {"ocupacion": ingreso.anterior["ocupacion"], "en_refugio": False,
                            "motivo": "traslado"}


def test_del_perfil_solo_quedan_los_nombres_de_los_campos():
    c = en_memoria()
    c.post("/adoptantes", json={"correo": "lau@correo.co", "nombre": "Laura",
                                "contrasena": CLAVE, "autoriza_datos": True})
    lau = h(c, "lau@correo.co")
    perfil = {"vivienda": "casa", "tiene_patio": True, "hay_ninos": True,
              "otros_animales": False, "horas_solo_al_dia": 4, "experiencia": True,
              "acepta_seguimiento": True}
    c.put("/adoptantes/yo/perfil", json=perfil, headers=lau)
    primero = ultimo(c, "PUT /adoptantes/yo/perfil")
    assert primero.anterior is None and len(primero.nuevo["campos"]) == 7
    c.put("/adoptantes/yo/perfil", json={**perfil, "horas_solo_al_dia": 9}, headers=lau)
    segundo = ultimo(c, "PUT /adoptantes/yo/perfil")
    assert segundo.nuevo == {"campos": ["horas_solo_al_dia"]}
    valores = repr((segundo.anterior, segundo.nuevo))
    assert "9" not in valores and "casa" not in valores


def test_el_administrador_ve_los_valores_en_la_bitacora():
    c = en_memoria()
    coord = h(c, "coord@patitas.co")
    c.post("/refugio/ingresos", json={"nombre": "Toby", "especie": "perro",
                                      "estado_salud": "sano"}, headers=coord)
    eventos = c.app.state.bitacora.recientes()
    assert any(e.nuevo for e in eventos)
