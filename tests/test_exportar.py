"""RF-31 (#102): exportar en CSV y PDF anonimizados."""
import csv
import io
from datetime import UTC, datetime, timedelta

from app.dominio.modelos import DecisionTriaje, EstadoReporte, Prioridad, Reporte, Ubicacion
from app.indicadores.exportar import a_csv, filas_anonimizadas
from tests.test_decision_adopcion import en_memoria, h

T0 = datetime(2026, 10, 29, 13, 47, tzinfo=UTC)
DESCRIPCION = "Perro herido frente a la casa de Doña Rosa, llamar al 3001234567"


def reporte():
    return Reporte("K7M2Q9XA", DESCRIPCION, Ubicacion(7.8939, -72.5078, "Calle 10 # 4-20", 6),
                   estado=EstadoReporte.CONFIRMADO, prioridad=Prioridad.ALTA, creado_en=T0)


def test_la_fila_no_permite_llegar_a_una_persona_ni_a_una_casa():
    decision = DecisionTriaje("K7M2Q9XA", "vet@patitas.co", Prioridad.ALTA, Prioridad.CRITICA,
                              "Sangra mucho", decidido_en=T0 + timedelta(minutes=12))
    (fila,) = filas_anonimizadas([reporte()], {"K7M2Q9XA": decision})
    assert fila == {"fila": 1, "dia": "2026-10-29", "comuna": 6, "estado": "confirmado",
                    "prioridad_sugerida": "alta", "prioridad_final": "critica",
                    "ajustada": "si", "minutos_hasta_confirmar": 12.0, "version_modelo": ""}
    texto = a_csv([fila])
    for prohibido in ("K7M2Q9XA", "Rosa", "300123", "Calle 10", "7.89", "vet@", "13:47"):
        assert prohibido not in texto


def test_csv_neutraliza_formulas():
    fila = {**filas_anonimizadas([reporte()], {})[0], "version_modelo": "=HYPERLINK(\"x\")"}
    (_, datos) = list(csv.reader(io.StringIO(a_csv([fila]))))
    assert datos[-1].startswith("'=")


def test_api_exportar_csv_y_pdf_solo_gestion():
    c = en_memoria()
    c.post("/reportes", json={"descripcion": DESCRIPCION, "direccion": "Calle 10 # 4-20",
                              "comuna": 6})
    coord = h(c, "coord@patitas.co")
    r = c.get("/indicadores/reportes.csv", headers=coord)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    assert "Rosa" not in r.text and r.text.splitlines()[0].startswith("fila,dia,comuna")
    pdf = c.get("/indicadores/resumen.pdf", headers=coord)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert b"Rosa" not in pdf.content
    assert c.get("/indicadores/reportes.csv").status_code == 401
