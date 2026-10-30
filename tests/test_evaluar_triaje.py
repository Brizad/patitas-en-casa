"""Comparación de clasificadores sobre la prueba fija (fase 7, RNF-03)."""
from app.dominio.modelos import Prioridad
from app.triaje.clasificador import Resultado
from scripts.ia.evaluar_triaje import CLASES, evaluar, matriz_confusion, metricas, tabla


def test_matriz_de_confusion_filas_reales_columnas_predichas():
    matriz = matriz_confusion(["critica", "critica", "baja"], ["critica", "alta", "baja"])
    assert matriz[0] == [1, 1, 0, 0] and matriz[3] == [0, 0, 0, 1]
    assert sum(map(sum, matriz)) == 3 and len(matriz) == len(CLASES) == 4


def test_precision_recall_y_f1_por_clase():
    m = metricas(["critica", "critica", "alta", "baja"], ["critica", "alta", "alta", "baja"])
    assert m["por_clase"]["critica"] == {"precision": 1.0, "recall": 0.5, "f1": 0.6667,
                                         "soporte": 2}
    assert m["por_clase"]["alta"]["precision"] == 0.5 and m["exactitud"] == 0.75
    assert m["por_clase"]["media"] == {"precision": 0.0, "recall": 0.0, "f1": 0.0, "soporte": 0}


def test_evaluar_separa_los_casos_dificiles_y_mide_el_tiempo():
    filas = [("perro atropellado", "critica", "comun"), ("gato privado", "critica", "frase_nueva"),
             ("tiene sarna", "baja", "comun")]

    def siempre_critica(_texto):
        return Resultado(Prioridad.CRITICA, 0.9, [])

    r = evaluar(siempre_critica, filas)
    assert r["por_clase"]["critica"]["recall"] == 1.0
    assert r["por_caso"]["frase_nueva"] == {"exactitud": 1.0, "reportes": 1,
                                            "recall_critica": 1.0}
    assert r["ms_por_reporte"] >= 0
    assert "| siempre |" in tabla({"siempre": r})
