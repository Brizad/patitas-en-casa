"""RF-30 (#102): indicadores sin datos personales."""
from datetime import UTC, datetime, timedelta

from app.dominio.modelos import (
    DecisionTriaje,
    EstadoReporte,
    Prioridad,
    Refugio,
    Reporte,
    Ubicacion,
)
from app.indicadores.calculo import Datos, calcular
from tests.test_decision_adopcion import en_memoria, h, preparar

T0 = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def reporte(codigo, version="reglas-v0"):
    return Reporte(codigo, "Perro herido cerca del parque principal", Ubicacion(direccion="x"),
                   estado=EstadoReporte.CONFIRMADO, prioridad=Prioridad.ALTA, creado_en=T0,
                   version_modelo=version)


def test_tiempos_y_acuerdo_por_version_del_modelo():
    reportes = [reporte("A"), reporte("B"), reporte("C", "reglas-v0+tfidf-lr-v1")]
    decisiones = {
        "A": DecisionTriaje("A", "v", Prioridad.ALTA, Prioridad.ALTA,
                            decidido_en=T0 + timedelta(minutes=10)),
        "B": DecisionTriaje("B", "v", Prioridad.ALTA, Prioridad.CRITICA, "Sangra mucho",
                            decidido_en=T0 + timedelta(minutes=30)),
        "C": DecisionTriaje("C", "v", Prioridad.ALTA, Prioridad.ALTA,
                            decidido_en=T0 + timedelta(minutes=20))}
    r = calcular(Datos(reportes, decisiones, [], [Refugio("Demo", 40, 30)], [], []),
                 T0)["reportes"]
    assert r["minutos_hasta_confirmar"] == {"mediana": 20.0, "promedio": 20.0}
    assert r["acuerdo_por_version_modelo"] == {
        "reglas-v0": {"decisiones": 2, "confirmadas_sin_cambio": 0.5},
        "reglas-v0+tfidf-lr-v1": {"decisiones": 1, "confirmadas_sin_cambio": 1.0}}
    assert r["por_prioridad_confirmada"] == {"alta": 2, "critica": 1}


def test_sin_datos_no_falla():
    vacio = calcular(Datos([], {}, [], [], [], []), T0)
    assert vacio["reportes"]["minutos_hasta_confirmar"]["mediana"] is None


def test_api_indicadores_para_coordinacion_y_administracion_sin_datos_personales():
    c = en_memoria()
    coord, _, ids = preparar(c)
    c.post(f"/refugio/solicitudes/{ids['lau@correo.co']}/decision", json={"aprobar": True},
           headers=coord)
    c.post("/reportes", json={"descripcion": "Gato atropellado en la calle 10, no se mueve",
                              "direccion": "Calle 10 # 4-20"})
    r = c.get("/indicadores", headers=coord)
    assert r.status_code == 200
    datos = r.json()
    assert datos["reportes"]["total"] == 1
    assert datos["adopciones"]["aprobadas"] == 1
    assert datos["adopciones"]["seguimientos"]["pendientes"] == 3
    assert "@" not in r.text and "Calle 10" not in r.text
    assert c.get("/indicadores").status_code == 401
    assert c.get("/indicadores", headers=h(c, "lau@correo.co")).status_code == 403
