"""RF-27 (visita previa) y RF-10 / RN-13 (devoluciones con su motivo), #113."""
import pytest

from tests.test_decision_adopcion import en_memoria, en_postgres, h, preparar

NOTA = "Visitar el sábado y revisar el patio y la reja"
MOTIVO = "La familia se muda a un apartamento sin espacio para ella"


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def c(request):
    if request.param == "postgres":
        return en_postgres(request.getfixturevalue("bd_limpia"))
    return en_memoria()


def test_pedir_visita_y_luego_aprobar(c):
    coord, _, ids = preparar(c)
    sid = ids["lau@correo.co"]
    r = c.post(f"/refugio/solicitudes/{sid}/visita", json={"texto": NOTA}, headers=coord)
    assert r.status_code == 200 and r.json() == {"id": sid, "estado": "visita", "nota": NOTA}
    otra = c.post(f"/refugio/solicitudes/{sid}/visita", json={"texto": NOTA}, headers=coord)
    assert otra.status_code == 409  # la visita se pide una vez
    aprobada = c.post(f"/refugio/solicitudes/{sid}/decision", json={"aprobar": True},
                      headers=coord)
    assert aprobada.json()["estado"] == "aprobada"


def test_la_nota_de_la_visita_no_puede_ser_relleno(c):
    coord, _, ids = preparar(c)
    r = c.post(f"/refugio/solicitudes/{ids['lau@correo.co']}/visita",
               json={"texto": ".........."}, headers=coord)
    assert r.status_code == 422


def test_devolucion_reingresa_al_animal_y_vuelve_al_catalogo(c):
    coord, animal_id, ids = preparar(c)
    sid = ids["lau@correo.co"]
    ruta = f"/refugio/solicitudes/{sid}/devolucion"
    assert c.post(ruta, json={"texto": MOTIVO}, headers=coord).status_code == 409  # pendiente
    c.post(f"/refugio/solicitudes/{sid}/decision", json={"aprobar": True}, headers=coord)
    antes = c.get("/refugio/ocupacion", headers=coord).json()["ocupacion"]
    r = c.post(ruta, json={"texto": MOTIVO}, headers=coord)
    assert r.status_code == 200 and r.json() == {"id": sid, "estado": "devuelta",
                                                 "motivo": MOTIVO}
    despues = c.get("/refugio/ocupacion", headers=coord).json()["ocupacion"]
    assert int(despues.split("/")[0]) == int(antes.split("/")[0]) + 1
    ficha = c.get(f"/refugio/animales/{animal_id}", headers=coord).json()
    assert ficha["egresado_en"] is None
    assert [a["animal_id"] for a in c.get("/adopciones/animales").json()] == [animal_id]
    indicadores = c.get("/indicadores", headers=coord).json()
    assert indicadores["adopciones"]["solicitudes_por_estado"]["devuelta"] == 1


def test_devolucion_solo_del_coordinador(c):
    coord, _, ids = preparar(c)
    ruta = f"/refugio/solicitudes/{ids['lau@correo.co']}/devolucion"
    assert c.post(ruta, json={"texto": MOTIVO}).status_code == 401
    assert c.post(ruta, json={"texto": MOTIVO},
                  headers=h(c, "lau@correo.co")).status_code == 403


@pytest.mark.postgres
def test_sin_cupo_la_devolucion_no_cambia_nada(bd_limpia):
    from tests.conftest import preparar_refugio
    c = en_postgres(bd_limpia)
    coord, animal_id, ids = preparar(c)
    sid = ids["lau@correo.co"]
    c.post(f"/refugio/solicitudes/{sid}/decision", json={"aprobar": True}, headers=coord)
    preparar_refugio(bd_limpia, 40, 40)  # refugio lleno
    r = c.post(f"/refugio/solicitudes/{sid}/devolucion", json={"texto": MOTIVO}, headers=coord)
    assert r.status_code == 409 and "cupo" in r.json()["detail"]
    mias = c.get("/adopciones/solicitudes/mias", headers=h(c, "lau@correo.co")).json()
    assert mias[0]["estado"] == "aprobada"
    assert c.get(f"/refugio/animales/{animal_id}", headers=coord).json()["egresado_en"]
