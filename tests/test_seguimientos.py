"""RF-10 (#85): seguimientos a los 30, 90 y 180 días de cada adopción."""
import pytest

from tests.test_decision_adopcion import en_memoria, en_postgres, h, preparar

NOTA = "Visita: come bien y duerme en la sala, la familia está contenta"


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def c(request):
    if request.param == "postgres":
        return en_postgres(request.getfixturevalue("bd_limpia"))
    return en_memoria()


def aprobada(c):
    coord, _, ids = preparar(c)
    c.post(f"/refugio/solicitudes/{ids['lau@correo.co']}/decision", json={"aprobar": True},
           headers=coord)
    return coord


def test_lista_los_tres_seguimientos_pendientes(c):
    coord = aprobada(c)
    lista = c.get("/refugio/seguimientos", headers=coord).json()
    assert [(x["dia"], x["animal"], x["vencido"]) for x in lista] == [
        (30, "Canela", False), (90, "Canela", False), (180, "Canela", False)]
    assert all(x["realizado_en"] is None for x in lista)


def test_registrar_un_seguimiento_una_sola_vez(c):
    coord = aprobada(c)
    primero = c.get("/refugio/seguimientos", headers=coord).json()[0]
    ruta = f"/refugio/seguimientos/{primero['id']}"
    assert c.post(ruta, json={"nota": "ok"}, headers=coord).status_code == 422
    r = c.post(ruta, json={"nota": NOTA}, headers=coord)
    assert r.status_code == 200 and r.json()["nota"] == NOTA
    assert r.json()["registrado_por"] == "coord@patitas.co"
    assert c.post(ruta, json={"nota": NOTA}, headers=coord).status_code == 409
    lista = c.get("/refugio/seguimientos", headers=coord).json()
    assert lista[-1]["dia"] == 30 and lista[-1]["realizado_en"] is not None  # hechos al final


def test_seguimientos_solo_del_coordinador(c):
    aprobada(c)
    assert c.get("/refugio/seguimientos").status_code == 401
    assert c.get("/refugio/seguimientos", headers=h(c, "lau@correo.co")).status_code == 403
    coord = h(c, "coord@patitas.co")
    assert c.post("/refugio/seguimientos/999", json={"nota": NOTA},
                  headers=coord).status_code == 404
