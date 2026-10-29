"""RF-09, RNF-16 (#95): compatibilidad adoptante–animal con puntaje, razones y sin sesgos."""
from dataclasses import fields, replace

import pytest

from app.adopciones.compatibilidad import ATRIBUTOS_USADOS, calcular, recomendar
from app.adopciones.modelos import Energia, PerfilAdoptante, Publicacion, Tamano, Vivienda
from tests.test_decision_adopcion import en_memoria, h, preparar

PERFIL = PerfilAdoptante("lau@correo.co", Vivienda.CASA, True, False, False, 4, True, True)


def animal(animal_id=1, **cambios):
    base = Publicacion(animal_id, "Perro juguetón y cariñoso con la gente", Tamano.MEDIANO,
                       Energia.MEDIA, 24, True, True, False, nombre=f"A{animal_id}")
    return replace(base, **cambios)


def test_hogar_ideal_da_100_y_tres_razones():
    c = calcular(PERFIL, animal())
    assert c.puntaje == 100 and len(c.razones) == 3 and c.recomendable and not c.alertas


def test_animal_grande_y_activo_en_apartamento_sin_experiencia_puntua_bajo():
    perfil = replace(PERFIL, vivienda=Vivienda.APARTAMENTO, tiene_patio=False,
                     horas_solo_al_dia=9, experiencia=False)
    c = calcular(perfil, animal(tamano=Tamano.GRANDE, energia=Energia.ALTA))
    assert c.puntaje < 50
    assert any("grande" in a for a in c.alertas) and any("solo 9 h" in a for a in c.alertas)


def test_restriccion_dura_da_cero_y_no_se_recomienda():
    con_ninos = replace(PERFIL, hay_ninos=True)
    c = calcular(con_ninos, animal(apto_ninos=False))
    assert c.puntaje == 0 and not c.recomendable and "niños" in c.restricciones[0]


def test_recomendar_ordena_y_excluye_las_restricciones():
    perfil = replace(PERFIL, otros_animales=True, horas_solo_al_dia=6)
    lista = recomendar(perfil, [animal(1, energia=Energia.ALTA, edad_meses=6),
                                animal(2), animal(3, apto_otros_animales=False)])
    assert [a.animal_id for a, _ in lista] == [2, 1]


def test_rnf16_el_perfil_no_tiene_atributos_protegidos():
    protegidos = {"edad", "genero", "sexo", "estrato", "etnia", "raza_persona", "religion",
                  "discapacidad", "estado_civil", "ingresos"}
    campos = {f.name for f in fields(PerfilAdoptante)}
    assert not campos & protegidos
    assert set(ATRIBUTOS_USADOS["perfil"]) <= campos


@pytest.mark.parametrize("correo", ["ana@correo.co", "zz@otro.org"])
def test_rnf16_el_puntaje_no_depende_de_quien_es_solo_del_hogar(correo):
    assert calcular(replace(PERFIL, correo=correo), animal()) == calcular(PERFIL, animal())


def test_api_recomendaciones_del_adoptante():
    c = en_memoria()
    preparar(c)  # Canela publicada, no apta con niños; Lau sin niños, Ana con niños
    lau = c.get("/adopciones/recomendaciones", headers=h(c, "lau@correo.co")).json()
    assert lau[0]["nombre"] == "Canela" and 0 < lau[0]["puntaje"] <= 100
    assert len(lau[0]["razones"]) == 3
    assert c.get("/adopciones/recomendaciones", headers=h(c, "ana@correo.co")).json() == []
    assert c.get("/adopciones/recomendaciones").status_code == 401
    solicitudes = c.get("/refugio/solicitudes", headers=h(c, "coord@patitas.co")).json()
    assert {s["adoptante"]: s["compatibilidad"]["puntaje"] for s in solicitudes}[
        "ana@correo.co"] == 0
