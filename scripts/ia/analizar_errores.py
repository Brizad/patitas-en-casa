"""Análisis de errores del triaje de texto con casos escritos como un ciudadano.

Uso: python -m scripts.ia.analizar_errores [scripts/ia/casos_ciudadanos_v1.json]

Pasa cada caso por el mismo clasificador que usa la API (reglas + modelo, `triaje_por_defecto`)
y muestra la matriz de confusión, el recall de «crítica» y los casos donde falla. Los casos
NO son datos reales: los escribió el asistente (ver el aviso dentro del JSON).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from app.dominio.modelos import Prioridad
from app.triaje.combinado import triaje_por_defecto

ORDEN = [Prioridad.CRITICA, Prioridad.ALTA, Prioridad.MEDIA, Prioridad.BAJA]
POR_DEFECTO = Path(__file__).with_name("casos_ciudadanos_v1.json")


def evaluar(ruta: Path = POR_DEFECTO) -> dict:
    clasificar, version = triaje_por_defecto()
    casos = json.loads(ruta.read_text(encoding="utf-8"))["casos"]
    matriz: Counter = Counter()
    errores = []
    for caso in casos:
        esperada = Prioridad(caso["esperada"])
        r = clasificar(caso["texto"])
        matriz[(esperada, r.prioridad)] += 1
        if r.prioridad != esperada:
            errores.append({"texto": caso["texto"], "esperada": esperada.value,
                            "sugerida": r.prioridad.value, "confianza": round(r.confianza, 2),
                            "evidencias": r.evidencias})
    criticas = sum(matriz[(Prioridad.CRITICA, p)] for p in ORDEN)
    return {"version": version, "total": len(casos), "matriz": matriz, "errores": errores,
            "aciertos": sum(matriz[(p, p)] for p in ORDEN),
            "recall_critica": matriz[(Prioridad.CRITICA, Prioridad.CRITICA)] / criticas,
            "criticas_bajo_alta": sum(matriz[(Prioridad.CRITICA, p)]
                                      for p in (Prioridad.MEDIA, Prioridad.BAJA))}


def imprimir(r: dict) -> None:
    print(f"Clasificador: {r['version']} · {r['total']} casos · aciertos {r['aciertos']} "
          f"({r['aciertos'] / r['total']:.1%})")
    print(f"Recall de crítica: {r['recall_critica']:.2f} · críticas sugeridas como media o "
          f"baja: {r['criticas_bajo_alta']}")
    print("\n| Real \\ Sugerida | " + " | ".join(p.value for p in ORDEN) + " |")
    print("|---|" + "---|" * len(ORDEN))
    for real in ORDEN:
        print(f"| {real.value} | " + " | ".join(str(r["matriz"][(real, s)]) for s in ORDEN)
              + " |")
    print("\nErrores:")
    for e in r["errores"]:
        print(f"- [{e['esperada']} → {e['sugerida']}, {e['confianza']}] {e['texto']} "
              f"· {e['evidencias']}")


if __name__ == "__main__":
    imprimir(evaluar(Path(sys.argv[1]) if len(sys.argv) > 1 else POR_DEFECTO))
