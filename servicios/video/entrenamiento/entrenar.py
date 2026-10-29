"""Entrena el clasificador de la marcha y lo exporta a JSON (#125, RF-03, DT-04).

Datos: medidas SINTÉTICAS. No hay todavía videos de perros y gatos etiquetados por
veterinarios, así que se generan medidas al azar y se etiquetan con criterios clínicos
sencillos (los mismos que explican las evidencias):

- crítica: no se pone de pie y casi no se mueve;
- alta: no apoya una pata o pasa la mayor parte del tiempo echado;
- media: cojea (asimetría ≥ 0,4) o el paso es irregular;
- baja: marcha normal.

Con un 4 % de etiquetas cambiadas al azar, para que el modelo no sea una copia exacta de las
reglas. Lo que mide la validación es qué tan bien el modelo aprende ESTOS criterios, no si
acierta con animales reales: eso exige videos etiquetados (DT-04). Cuando existan, se pasa
un CSV con las cinco entradas y la prioridad del veterinario:

    python servicios/video/entrenamiento/entrenar.py --datos medidas_etiquetadas.csv

scikit-learn se usa solo aquí; el trabajador lee el JSON con Python puro.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from sklearn.metrics import classification_report, recall_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

SALIDA = Path(__file__).resolve().parents[1] / "patitas_video" / "modelo_marcha_v1.json"
ENTRADAS = ["sin_ponerse_de_pie", "asimetria", "sin_apoyo", "irregularidad", "quietud"]
CLASES = ["critica", "alta", "media", "baja"]


def etiqueta(x: list[float]) -> str:
    sin_pie, asimetria, sin_apoyo, irregular, quieto = x
    if sin_pie > 0.8 and quieto > 0.9:
        return "critica"
    if sin_apoyo >= 0.7 or sin_pie > 0.5:
        return "alta"
    if asimetria >= 0.4 or irregular >= 0.4:
        return "media"
    return "baja"


def generar(por_clase: int = 2000, semilla: int = 7) -> tuple[list[list[float]], list[str]]:
    """El mismo número de ejemplos de cada prioridad: al azar, «crítica» saldría en menos
    del 2 % de los casos y el modelo aprendería a no decirla nunca."""
    azar = random.Random(semilla)
    xs, ys, cuenta = [], [], dict.fromkeys(CLASES, 0)
    while min(cuenta.values()) < por_clase:
        x = [round(azar.random(), 3) for _ in ENTRADAS]
        y = etiqueta(x)
        if cuenta[y] >= por_clase:
            continue
        cuenta[y] += 1
        xs.append(x)
        ys.append(azar.choice(CLASES) if azar.random() < 0.04 else y)
    return xs, ys


def leer_csv(ruta: Path) -> tuple[list[list[float]], list[str]]:
    with ruta.open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    return [[float(f[c]) for c in ENTRADAS] for f in filas], [f["prioridad"] for f in filas]


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--datos", type=Path, help="CSV con medidas etiquetadas")
    datos = argumentos.parse_args().datos
    xs, ys = leer_csv(datos) if datos else generar()
    x_ent, x_val, y_ent, y_val = train_test_split(xs, ys, test_size=0.2, random_state=7,
                                                  stratify=ys)
    escala = StandardScaler().fit(x_ent)
    red = MLPClassifier(hidden_layer_sizes=(8,), max_iter=2000, random_state=7)
    red.fit(escala.transform(x_ent), y_ent)
    predichas = red.predict(escala.transform(x_val))
    print(classification_report(y_val, predichas, digits=3))
    print("recall de crítica:", round(recall_score(y_val, predichas, labels=["critica"],
                                                    average="macro"), 3))
    orden = [list(red.classes_).index(c) for c in CLASES]
    capas = [{"pesos": w.tolist(), "sesgos": b.tolist()}
             for w, b in zip(red.coefs_[:-1], red.intercepts_[:-1], strict=True)]
    capas.append({"pesos": [[fila[j] for j in orden] for fila in red.coefs_[-1].tolist()],
                  "sesgos": [red.intercepts_[-1][j] for j in orden]})
    SALIDA.write_text(json.dumps({
        "version": "marcha-mlp-v1", "entradas": ENTRADAS, "clases": CLASES,
        "datos": f"etiquetados por veterinarios ({datos.name})" if datos
        else "sintéticos: medidas al azar etiquetadas con criterios clínicos sencillos",
        "media": escala.mean_.tolist(), "escala": escala.scale_.tolist(), "capas": capas},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("modelo escrito en", SALIDA)


if __name__ == "__main__":
    main()
