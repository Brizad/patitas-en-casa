"""RF-30, RF-31 y RNF-16 completos (#117): tiempos por prioridad, devoluciones, fichas en
CSV y tasa de recomendación por segmento."""
from datetime import UTC, datetime, timedelta

from app.adopciones.modelos import Energia, PerfilAdoptante, Publicacion, Tamano, Vivienda
from app.dominio.modelos import (
    DecisionTriaje,
    EstadoReporte,
    EstadoRescate,
    Prioridad,
    Reporte,
    Rescate,
    Ubicacion,
)
from app.indicadores.calculo import Datos, calcular
from tests.test_decision_adopcion import en_memoria, h, preparar

T0 = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def test_tiempos_de_respuesta_por_prioridad():
    r = Reporte("A", "Perro herido cerca del parque principal", Ubicacion(direccion="x"),
                estado=EstadoReporte.CONFIRMADO, creado_en=T0)
    dec = DecisionTriaje("A", "v", Prioridad.CRITICA, Prioridad.CRITICA,
                         decidido_en=T0 + timedelta(minutes=8))
    resc = Rescate("A", "r@x.co", EstadoRescate.EN_CAMINO, T0 + timedelta(minutes=20),
                   T0 + timedelta(minutes=20))
    tiempos = calcular(Datos([r], {"A": dec}, [resc], [], [], []), T0)["reportes"][
        "tiempos_por_prioridad"]
    assert tiempos == {"critica": {"mediana_minutos_hasta_confirmar": 8.0,
                                   "mediana_minutos_hasta_aceptar_rescate": 12.0}}


def test_rnf16_tasa_de_recomendacion_por_segmento():
    apto = Publicacion(1, "x" * 20, Tamano.PEQUENO, Energia.BAJA, 24, True, True, False)
    sin_ninos = Publicacion(2, "x" * 20, Tamano.PEQUENO, Energia.BAJA, 24, False, True, False)
    perfiles = (PerfilAdoptante("a@x.co", Vivienda.CASA, True, True, False, 4, True, True),
                PerfilAdoptante("b@x.co", Vivienda.CASA, True, False, False, 4, True, True))
    seg = calcular(Datos([], {}, [], [], [], [], perfiles, (apto, sin_ninos)), T0)[
        "adopciones"]["tasa_recomendacion_por_segmento"]
    assert seg["con niños"] == {"perfiles": 1, "tasa_recomendacion": 0.5}
    assert seg["sin niños"] == {"perfiles": 1, "tasa_recomendacion": 1.0}
    assert seg["vivienda: casa"]["perfiles"] == 2


def test_api_fichas_csv_y_devoluciones_en_indicadores():
    c = en_memoria()
    coord, animal_id, ids = preparar(c)
    c.post(f"/refugio/animales/{animal_id}/historial", json={"tipo": "observacion",
           "texto": "Doña Rosa la trajo, come bien"}, headers=coord)  # 403: es del vet
    r = c.get("/indicadores/fichas.csv", headers=coord)
    assert r.status_code == 200 and r.text.splitlines()[0].startswith("id,especie,ingreso")
    assert "Rosa" not in r.text
    assert c.get("/indicadores/fichas.csv").status_code == 401
    assert c.get("/indicadores/fichas.csv", headers=h(c, "lau@correo.co")).status_code == 403
    datos = c.get("/indicadores", headers=coord).json()
    assert datos["adopciones"]["devoluciones"] == 0
    assert "con niños" in datos["adopciones"]["tasa_recomendacion_por_segmento"]
