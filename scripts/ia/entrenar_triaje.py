"""Entrena el clasificador de triaje y lo exporta a JSON (fase 4, #95, RF-02, RNF-03).

Modelo: TF-IDF (palabras y pares de palabras) + regresión logística. ¿Por qué este y no un
Transformer? Cabe de sobra en los 512 MB de Render (el JSON pesa cientos de KB), responde en
milisegundos (RNF-01: 3 s) y cada decisión se explica con las palabras que más pesaron
(RNF-09). scikit-learn se usa SOLO aquí, para entrenar: en producción el modelo se lee del
JSON con Python puro (app/triaje/modelo.py).

Para cambiarlo por uno más grande (por ejemplo un BERT en español como BETO): entrenarlo con
los mismos datos, exportarlo a ONNX, escribir otro adaptador con la misma firma
`clasificar(texto) -> Resultado` y medirlo con este mismo script de validación; solo se
cambia si supera el recall de «crítica» y cabe en la memoria del servidor.

RNF-03 (recall ≥ 0,95 en crítica): perder un caso crítico es mucho peor que revisar uno de
más. Por eso, después de entrenar, se baja el umbral de «crítica» hasta que el recall en
validación llegue a 0,97 (margen sobre 0,95).

Uso:  python scripts/ia/entrenar_triaje.py   (genera los datos sintéticos y escribe el JSON)
      python scripts/ia/entrenar_triaje.py --v2 salida/tfidf_v2.json   (datos v2, fase 7)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import classification_report, recall_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402

from app.triaje.normalizacion import normalizar  # noqa: E402
from scripts.ia.generar_datos_sinteticos import generar  # noqa: E402

VERSION = "tfidf-lr-v1"
SALIDA = RAIZ / "app" / "triaje" / "modelo_tfidf_v1.json"
RECALL_OBJETIVO = 0.97


def entrenar(cantidad: int = 4000, semilla: int = 42, datos: list | None = None,
             version: str = VERSION, origen: str = "scripts/ia/generar_datos_sinteticos.py"
             ) -> dict:
    """Con `datos` [(texto, prioridad)] entrena con esos (fase 7: datos v2)."""
    textos, etiquetas = zip(*(datos or generar(cantidad, semilla)), strict=True)
    cantidad = len(textos)
    x_ent, x_val, y_ent, y_val = train_test_split(
        textos, etiquetas, test_size=0.2, stratify=etiquetas, random_state=semilla)
    vectorizador = TfidfVectorizer(preprocessor=normalizar, ngram_range=(1, 2), min_df=2)
    modelo = LogisticRegression(max_iter=3000, C=4.0)
    modelo.fit(vectorizador.fit_transform(x_ent), y_ent)

    clases = list(modelo.classes_)
    prob_val = modelo.predict_proba(vectorizador.transform(x_val))
    i_critica = clases.index("critica")
    umbral = 0.5
    while umbral > 0.05:
        pred = [("critica" if p[i_critica] >= umbral else clases[max(range(len(p)),
                 key=p.__getitem__)]) for p in prob_val]
        if recall_score(y_val, pred, labels=["critica"], average=None)[0] >= RECALL_OBJETIVO:
            break
        umbral -= 0.05
    reporte = classification_report(y_val, pred, output_dict=True, zero_division=0)
    print(classification_report(y_val, pred, zero_division=0))
    print(f"Umbral de crítica: {umbral:.2f}")

    vocabulario = vectorizador.vocabulary_
    terminos = sorted(vocabulario, key=vocabulario.get)
    return {
        "version": version,
        "datos": f"sintéticos: {cantidad} reportes, semilla {semilla} ({origen})",
        "clases": clases,
        "terminos": terminos,
        "idf": [round(float(v), 5) for v in vectorizador.idf_],
        "coeficientes": [[round(float(v), 5) for v in fila] for fila in modelo.coef_],
        "intercepto": [round(float(v), 5) for v in modelo.intercept_],
        "umbral_critica": round(umbral, 2),
        "metricas_validacion": {
            "exactitud": round(reporte["accuracy"], 4),
            **{c: {"recall": round(reporte[c]["recall"], 4),
                   "precision": round(reporte[c]["precision"], 4)} for c in clases},
        },
    }


if __name__ == "__main__":
    if "--v2" in sys.argv:  # fase 7: mismo método con los datos v2, para comparar
        from scripts.ia.datos_triaje import conjuntos
        filas = [(t, e) for nombre in ("entrenamiento", "validacion")
                 for t, e, _ in conjuntos()[nombre]]
        SALIDA = Path(sys.argv[sys.argv.index("--v2") + 1])
        exportado = entrenar(datos=filas, version="tfidf-lr-v2",
                             origen="scripts/ia/datos_triaje.py")
    else:
        exportado = entrenar()
    SALIDA.write_text(json.dumps(exportado, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
    print(f"Modelo guardado en {SALIDA} "
          f"({SALIDA.stat().st_size // 1024} KB, {len(exportado['terminos'])} términos)")
