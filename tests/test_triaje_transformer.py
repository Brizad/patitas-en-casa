"""El Transformer real (mALBERT ONNX int8) en la API (fase 7, RF-02, RNF-03, RN-02, RN-03).

Corren solo si los archivos del modelo están en app/triaje/onnx/ (hoy no están en el
repositorio: ver docs/aprende/fase-7-transformers.md) y onnxruntime y tokenizers están
instalados. El flujo entrenar-triaje.yml las corre con cada modelo recién afinado: son la
puerta para publicarlo (recall de crítica ≥ 0,95 en la prueba fija, RNF-03).
"""
import json

import pytest

from app.triaje.modelo_onnx import DIRECTORIO, METADATOS  # noqa: E402

if not (DIRECTORIO / METADATOS).exists():
    pytest.skip("el modelo ONNX no está en app/triaje/onnx/", allow_module_level=True)
pytest.importorskip("onnxruntime")
pytest.importorskip("tokenizers")

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion  # noqa: E402
from app.triaje.combinado import clasificador_combinado, triaje_por_defecto  # noqa: E402
from app.triaje.modelo_onnx import cargar_modelo_onnx  # noqa: E402
from app.triaje.servicio import ServicioTriaje  # noqa: E402
from scripts.ia.datos_triaje import leer  # noqa: E402
from scripts.ia.evaluar_triaje import PRUEBA  # noqa: E402


@pytest.fixture(scope="module")
def modelo():
    return cargar_modelo_onnx()


def reporte(descripcion):
    return Reporte(codigo="MALB0001", descripcion=descripcion,
                   ubicacion=Ubicacion(direccion="Calle 10"))


def test_el_modelo_cita_su_licencia():
    metadatos = json.loads((DIRECTORIO / METADATOS).read_text(encoding="utf-8"))
    assert metadatos["licencia"].startswith("Apache-2.0")


def test_la_api_usa_reglas_mas_transformer_y_lo_dice_en_la_version(monkeypatch):
    monkeypatch.delenv("PATITAS_TRIAJE_TRANSFORMER", raising=False)
    clasificador, version = triaje_por_defecto()
    assert version == "reglas-v0+malbert-onnx-v1"
    assert clasificador("Gato convulsionando en la calle 10").prioridad == Prioridad.CRITICA


def test_entiende_jerga_que_las_reglas_no_conocen(modelo):
    r = modelo.clasificar("parce la moto lo levanto y quedo tieso en la avenida 0, ayudaaa")
    assert r.prioridad == Prioridad.CRITICA and len(r.evidencias) == 2


def test_recall_de_critica_en_la_prueba_fija_cumple_rnf03(modelo):
    """Reglas + Transformer (lo que usa la API) sobre los críticos de la prueba fija."""
    clasificar = clasificador_combinado(modelo)
    criticos = [t for t, e, _ in leer(PRUEBA) if e == "critica"]
    hallados = sum(clasificar(t).prioridad == Prioridad.CRITICA for t in criticos)
    assert hallados / len(criticos) >= 0.95


def test_rn02_rn03_se_conservan_con_el_modelo_real(modelo):
    servicio = ServicioTriaje(clasificador_combinado(modelo), version="v")
    dudoso = servicio.evaluar(reporte("Hola, un gatico en Caobos anda vagando por la cuadra"))
    if dudoso.prioridad in (Prioridad.MEDIA, Prioridad.BAJA):
        assert (dudoso.confianza < 0.6) == (dudoso.estado == EstadoReporte.REQUIERE_REVISION)
    else:  # crítica y alta nunca se degradan (RN-02)
        assert dudoso.estado == EstadoReporte.CLASIFICADO
    sin_tiempo = ServicioTriaje(clasificador_combinado(modelo), tiempo_max_s=0, version="v")
    evaluado = sin_tiempo.evaluar(reporte("Un perro atropellado en la avenida 0, no se mueve"))
    assert (evaluado.prioridad, evaluado.estado) == (Prioridad.ALTA, EstadoReporte.SIN_CLASIFICAR)
