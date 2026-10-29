"""Clasificador entrenado y su combinación con las reglas (fase 4, #95, RF-02, RNF-03, RNF-09)."""
import json

import pytest

from app.dominio.modelos import Prioridad
from app.triaje.clasificador import Resultado
from app.triaje.combinado import combinar, triaje_por_defecto
from app.triaje.modelo import ARCHIVO, cargar_modelo
from scripts.ia.generar_datos_sinteticos import generar


def test_el_modelo_publicado_cumple_rnf03_en_su_validacion():
    metricas = json.loads(ARCHIVO.read_text(encoding="utf-8"))["metricas_validacion"]
    assert metricas["critica"]["recall"] >= 0.95


def test_el_modelo_acierta_con_datos_sinteticos_de_otra_semilla():
    """Datos que no vio al entrenar (misma fuente sintética: no prueba casos reales)."""
    modelo = cargar_modelo()
    datos = generar(400, semilla=7)
    criticos = [t for t, e in datos if e == "critica"]
    halla = sum(modelo.clasificar(t).prioridad == Prioridad.CRITICA for t in criticos)
    assert halla / len(criticos) >= 0.95
    assert sum(modelo.clasificar(t).prioridad.value == e for t, e in datos) / len(datos) >= 0.9


def test_reproduce_las_probabilidades_de_scikit_learn():
    """La inferencia en Python puro debe dar lo mismo que scikit-learn (si está instalado)."""
    pytest.importorskip("sklearn")
    from scripts.ia.entrenar_triaje import entrenar  # entrena de nuevo, determinista

    exportado = entrenar(cantidad=800)
    from app.triaje.modelo import ModeloTriaje
    modelo = ModeloTriaje(exportado)
    probs = modelo.probabilidades("Un perro atropellado en la avenida, no se mueve")
    assert abs(sum(probs.values()) - 1) < 1e-9
    assert max(probs, key=probs.get) == Prioridad.CRITICA


def test_da_al_menos_tres_evidencias_con_texto_suficiente():
    r = cargar_modelo().clasificar("Un perro atropellado frente al parque, no se mueve")
    assert len(r.evidencias) >= 3 and all("apunta a" in e for e in r.evidencias)


def test_el_modelo_puede_subir_la_prioridad_pero_nunca_bajarla():
    reglas = Resultado(Prioridad.CRITICA, 0.8, ["señal: atropellad"])
    modelo = Resultado(Prioridad.BAJA, 0.9, ["«sarna» apunta a baja"])
    assert combinar(reglas, modelo, "v").prioridad == Prioridad.CRITICA
    sube = combinar(Resultado(Prioridad.BAJA, 0.3, []),
                    Resultado(Prioridad.ALTA, 0.7, ["«fractura» apunta a alta"]), "v")
    assert (sube.prioridad, sube.confianza) == (Prioridad.ALTA, 0.7)


def test_misma_prioridad_conserva_la_confianza_de_las_reglas():
    """Sin señales conocidas el reporte sigue yendo a revisión humana (RN-02)."""
    r = combinar(Resultado(Prioridad.BAJA, 0.3, []), Resultado(Prioridad.BAJA, 0.95, []), "v")
    assert r.confianza == 0.3 and len(r.evidencias) >= 3


def test_la_api_usa_reglas_mas_modelo_y_lo_dice_en_la_version():
    clasificador, version = triaje_por_defecto()
    assert version == "reglas-v0+tfidf-lr-v1"
    assert clasificador("Gato convulsionando en la calle 10").prioridad == Prioridad.CRITICA
