"""Compara clasificadores de triaje sobre el MISMO conjunto de prueba fijo (fase 7, RNF-03).

Métricas por clase (precisión, recall, F1), matriz de confusión 4×4 (filas = prioridad real,
columnas = la que sugirió el modelo) y recall de «crítica» por tipo de caso (comunes, frases
nuevas, negaciones, ruido fuerte). Python puro: no necesita scikit-learn.

Uso:  python scripts/ia/evaluar_triaje.py [--onnx-dir app/triaje/onnx] [--tfidf otro.json]
                                          [--salida metricas.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from app.triaje.clasificador import Resultado, clasificar  # noqa: E402
from app.triaje.combinado import clasificador_combinado  # noqa: E402
from app.triaje.modelo import cargar_modelo  # noqa: E402
from scripts.ia.datos_triaje import leer  # noqa: E402

CLASES = ["critica", "alta", "media", "baja"]
PRUEBA = RAIZ / "scripts" / "ia" / "datos" / "triaje_prueba.csv"


def matriz_confusion(reales: list[str], predichas: list[str]) -> list[list[int]]:
    matriz = [[0] * len(CLASES) for _ in CLASES]
    for real, predicha in zip(reales, predichas, strict=True):
        matriz[CLASES.index(real)][CLASES.index(predicha)] += 1
    return matriz


def _dividir(a: float, b: float) -> float:
    return round(a / b, 4) if b else 0.0


def metricas(reales: list[str], predichas: list[str]) -> dict:
    matriz = matriz_confusion(reales, predichas)
    por_clase = {}
    for i, clase in enumerate(CLASES):
        aciertos = matriz[i][i]
        precision = _dividir(aciertos, sum(fila[i] for fila in matriz))
        recall = _dividir(aciertos, sum(matriz[i]))
        por_clase[clase] = {"precision": precision, "recall": recall,
                            "f1": _dividir(2 * precision * recall, precision + recall),
                            "soporte": sum(matriz[i])}
    return {"exactitud": _dividir(sum(matriz[i][i] for i in range(len(CLASES))), len(reales)),
            "f1_macro": round(sum(c["f1"] for c in por_clase.values()) / len(CLASES), 4),
            "por_clase": por_clase, "matriz": matriz}


def evaluar(clasificador: Callable[[str], Resultado], filas: list[tuple[str, str, str]]) -> dict:
    inicio = time.perf_counter()
    predichas = [clasificador(texto).prioridad.value for texto, _, _ in filas]
    milisegundos = (time.perf_counter() - inicio) * 1000 / len(filas)
    reales = [etiqueta for _, etiqueta, _ in filas]
    resultado = metricas(reales, predichas)
    resultado["ms_por_reporte"] = round(milisegundos, 2)
    resultado["por_caso"] = {}
    for caso in dict.fromkeys(c for _, _, c in filas):
        indices = [i for i, f in enumerate(filas) if f[2] == caso]
        sub = metricas([reales[i] for i in indices], [predichas[i] for i in indices])
        resultado["por_caso"][caso] = {"exactitud": sub["exactitud"], "reportes": len(indices),
                                       "recall_critica": sub["por_clase"]["critica"]["recall"]}
    return resultado


def clasificadores(onnx_dir: Path | None = None,
                   tfidf: Path | None = None) -> dict[str, Callable[[str], Resultado]]:
    """Lo que hoy usa la API (reglas + TF-IDF v1) y, si se piden, los modelos nuevos."""
    tfidf_v1 = cargar_modelo()
    lista = {"reglas-v0": clasificar, tfidf_v1.version: tfidf_v1.clasificar,
             f"reglas-v0+{tfidf_v1.version}": clasificador_combinado(tfidf_v1)}
    for modelo in _modelos_extra(onnx_dir, tfidf):
        lista[modelo.version] = modelo.clasificar
        lista[f"reglas-v0+{modelo.version}"] = clasificador_combinado(modelo)
    return lista


def _modelos_extra(onnx_dir: Path | None, tfidf: Path | None) -> list:
    extra = []
    if tfidf:
        from app.triaje.modelo import ModeloTriaje
        extra.append(ModeloTriaje(json.loads(tfidf.read_text(encoding="utf-8"))))
    if onnx_dir:
        from app.triaje.modelo_onnx import ModeloOnnx
        extra.append(ModeloOnnx.desde_directorio(onnx_dir))
    return extra


def tabla(resultados: dict[str, dict]) -> str:
    lineas = ["| Clasificador | Exactitud | F1 macro | Recall crítica | Precisión crítica "
              "| Recall crítica (difíciles) | ms/reporte |", "|---|---|---|---|---|---|---|"]
    for nombre, r in resultados.items():
        critica = r["por_clase"]["critica"]
        dificiles = [c["recall_critica"] for caso, c in r["por_caso"].items()
                     if caso != "comun" and caso != "negacion"]
        lineas.append(f"| {nombre} | {r['exactitud']:.3f} | {r['f1_macro']:.3f} | "
                      f"{critica['recall']:.3f} | {critica['precision']:.3f} | "
                      f"{min(dificiles, default=0):.3f} | {r['ms_por_reporte']} |")
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prueba", type=Path, default=PRUEBA)
    parser.add_argument("--onnx-dir", type=Path)
    parser.add_argument("--tfidf", type=Path, help="otro JSON de TF-IDF (p. ej. reentrenado)")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    filas = leer(args.prueba)
    resultados = {nombre: evaluar(c, filas)
                  for nombre, c in clasificadores(args.onnx_dir, args.tfidf).items()}
    print(tabla(resultados))
    if args.salida:
        args.salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=1),
                               encoding="utf-8")


if __name__ == "__main__":
    main()
