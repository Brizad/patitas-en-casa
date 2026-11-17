"""Valida (y, si se pide, reentrena) el triaje con reportes REALES confirmados por veterinarios.

Es el paso que falta para pagar DT-04 y para poder afirmar RNF-03 (recall de «crítica» ≥ 0,95).
Hasta que este script corra con datos reales, las métricas del proyecto son de datos
sintéticos o escritos por el asistente y NO son una validación.

    python -m scripts.ia.validar_con_reales datos_reales_triaje.csv
    python -m scripts.ia.validar_con_reales datos_reales_triaje.csv --reentrenar

El CSV tiene dos columnas, `descripcion,prioridad` (la prioridad FINAL que confirmó el
veterinario: critica, alta, media o baja). Cómo sacarlo de la base y por qué ese archivo no se
sube a git (trae texto escrito por ciudadanos): docs/tesis/triaje-ia.md.

Sin `--reentrenar`: mide el clasificador que hoy usa la API (reglas + modelo) contra todos los
casos y dice, con su intervalo de confianza, si RNF-03 cumple, no cumple o aún no se puede
saber. Con `--reentrenar`: aparta el 30 % de los casos reales como prueba (nunca se usan para
entrenar), entrena un candidato con los sintéticos más el 70 % real y compara candidato y
actual sobre la MISMA prueba. Solo recomienda cambiar si el candidato cumple RNF-03 y no pierde
recall de «crítica». Nunca reemplaza el modelo publicado: escribe un archivo candidato.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from app.dominio.modelos import Prioridad
from app.triaje.clasificador import Resultado
from app.triaje.combinado import clasificador_combinado, triaje_por_defecto
from app.triaje.modelo import ModeloTriaje

ORDEN = [Prioridad.CRITICA, Prioridad.ALTA, Prioridad.MEDIA, Prioridad.BAJA]
RECALL_RNF03 = 0.95
# Con menos críticas que estas el intervalo es tan ancho que no se puede concluir nada.
MIN_CRITICAS = 30
FRACCION_PRUEBA = 0.3
Caso = tuple[str, Prioridad]


class DatosInvalidos(ValueError):
    pass


def leer(ruta: Path) -> list[Caso]:
    """Lee el CSV; un error nombra la fila. Los textos repetidos cuentan una sola vez."""
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        filas = csv.DictReader(archivo)
        if not {"descripcion", "prioridad"} <= set(filas.fieldnames or []):
            raise DatosInvalidos("El CSV debe tener las columnas «descripcion» y «prioridad».")
        casos: dict[str, Prioridad] = {}
        for numero, fila in enumerate(filas, start=2):
            texto = (fila["descripcion"] or "").strip()
            try:
                prioridad = Prioridad((fila["prioridad"] or "").strip().lower())
            except ValueError as error:
                raise DatosInvalidos(f"Fila {numero}: prioridad «{fila['prioridad']}» no es "
                                     "critica, alta, media ni baja.") from error
            if not texto:
                raise DatosInvalidos(f"Fila {numero}: la descripción está vacía.")
            if casos.setdefault(texto, prioridad) != prioridad:
                raise DatosInvalidos(f"Fila {numero}: el mismo texto aparece con dos "
                                     "prioridades distintas; revísalo con el veterinario.")
    return list(casos.items())


def wilson(aciertos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza del 95 % de una proporción (Wilson): con pocos casos es ancho."""
    if total == 0:
        return 0.0, 1.0
    p, z2 = aciertos / total, z * z
    centro = (p + z2 / (2 * total)) / (1 + z2 / total)
    margen = z * math.sqrt(p * (1 - p) / total + z2 / (4 * total * total)) / (1 + z2 / total)
    return max(0.0, centro - margen), min(1.0, centro + margen)


def medir(clasificar: Callable[[str], Resultado], casos: list[Caso]) -> dict:
    matriz: Counter = Counter((real, clasificar(texto).prioridad) for texto, real in casos)
    criticas = sum(matriz[(Prioridad.CRITICA, p)] for p in ORDEN)
    halladas = matriz[(Prioridad.CRITICA, Prioridad.CRITICA)]
    return {"total": len(casos), "matriz": matriz, "criticas": criticas, "halladas": halladas,
            "aciertos": sum(matriz[(p, p)] for p in ORDEN),
            "recall_critica": halladas / criticas if criticas else None,
            "intervalo": wilson(halladas, criticas),
            "criticas_como_media_o_baja": sum(matriz[(Prioridad.CRITICA, p)]
                                              for p in (Prioridad.MEDIA, Prioridad.BAJA))}


def veredicto(medida: dict) -> str:
    """RNF-03 sin trampas: con pocas críticas no se afirma nada, salga el número que salga."""
    if medida["criticas"] < MIN_CRITICAS:
        return (f"AÚN NO SE PUEDE SABER: hay {medida['criticas']} casos críticos y hacen falta "
                f"al menos {MIN_CRITICAS} para decir algo de RNF-03.")
    recall, (bajo, alto) = medida["recall_critica"], medida["intervalo"]
    rango = f"recall {recall:.2f}, IC 95 % de {bajo:.2f} a {alto:.2f}"
    if recall < RECALL_RNF03:
        return f"NO CUMPLE RNF-03 ({rango})."
    if bajo < RECALL_RNF03:
        return (f"CUMPLE RNF-03 EN ESTA MUESTRA ({rango}), pero el intervalo baja de "
                f"{RECALL_RNF03}: con más casos críticos se sabrá si se sostiene.")
    return f"CUMPLE RNF-03 ({rango})."


def partir(casos: list[Caso], semilla: int = 42) -> tuple[list[Caso], list[Caso]]:
    """(entrenamiento, prueba) estratificado por prioridad; con la misma semilla, lo mismo."""
    rng, entrenamiento, prueba = random.Random(semilla), [], []
    for prioridad in ORDEN:
        grupo = sorted(c for c in casos if c[1] == prioridad)
        rng.shuffle(grupo)
        corte = round(len(grupo) * FRACCION_PRUEBA)
        prueba += grupo[:corte]
        entrenamiento += grupo[corte:]
    return entrenamiento, prueba


def recomendar(actual: dict, candidato: dict) -> str:
    if candidato["criticas"] < MIN_CRITICAS:
        return "NO CAMBIAR: la prueba tiene muy pocas críticas para comparar."
    if candidato["recall_critica"] < RECALL_RNF03:
        return "NO CAMBIAR: el candidato no cumple RNF-03 en la prueba real."
    if candidato["recall_critica"] < actual["recall_critica"]:
        return "NO CAMBIAR: el candidato halla menos críticas que el modelo actual."
    if candidato["aciertos"] <= actual["aciertos"]:
        return "NO CAMBIAR: el candidato no acierta más que el modelo actual."
    return ("CANDIDATO MEJOR: cumple RNF-03, no pierde críticas y acierta más. Antes de "
            "publicarlo, que un veterinario revise sus errores y Brayan lo apruebe.")


def informe(titulo: str, medida: dict) -> str:
    lineas = [f"## {titulo}", "",
              f"Casos: {medida['total']} · aciertos: {medida['aciertos']} "
              f"({medida['aciertos'] / medida['total']:.1%}) · críticas: {medida['criticas']} "
              f"(halladas {medida['halladas']}; sugeridas como media o baja: "
              f"{medida['criticas_como_media_o_baja']})", "", veredicto(medida), "",
              "| Real \\ Sugerida | " + " | ".join(p.value for p in ORDEN) + " |",
              "|---|" + "---|" * len(ORDEN)]
    lineas += [f"| {real.value} | " + " | ".join(str(medida["matriz"][(real, s)]) for s in ORDEN)
               + " |" for real in ORDEN]
    return "\n".join(lineas)


def reentrenar(casos: list[Caso], salida: Path, semilla: int = 42) -> str:
    from scripts.ia.entrenar_triaje import entrenar  # scikit-learn: solo al reentrenar

    entrenamiento, prueba = partir(casos, semilla)
    exportado = entrenar(semilla=semilla, version="tfidf-lr-candidato",
                         extra=[(texto, prioridad.value) for texto, prioridad in entrenamiento])
    salida.write_text(json.dumps(exportado, ensure_ascii=False, separators=(",", ":")), "utf-8")
    actual = medir(triaje_por_defecto()[0], prueba)
    candidato = medir(clasificador_combinado(ModeloTriaje(exportado)), prueba)
    return "\n\n".join([
        f"Prueba real apartada: {len(prueba)} casos que ningún modelo vio al entrenar "
        f"({len(entrenamiento)} reales entraron al entrenamiento del candidato).",
        informe("Modelo actual, en la prueba real", actual),
        informe("Candidato, en la misma prueba real", candidato),
        f"**{recomendar(actual, candidato)}**", f"Candidato guardado en {salida} (no se usa "
        "en la API hasta que se copie a app/triaje/ con una versión nueva)."])


def main(argumentos: list[str] | None = None) -> int:
    opciones = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    opciones.add_argument("csv", type=Path)
    opciones.add_argument("--reentrenar", action="store_true")
    opciones.add_argument("--salida", type=Path, default=Path("modelo_triaje_candidato.json"))
    o = opciones.parse_args(argumentos)
    try:
        casos = leer(o.csv)
    except DatosInvalidos as error:
        print(f"Datos inválidos: {error}")
        return 2
    clasificar, version = triaje_por_defecto()
    print(informe(f"Clasificador actual ({version}) con {len(casos)} reportes reales",
                  medir(clasificar, casos)))
    if o.reentrenar:
        print("\n" + reentrenar(casos, o.salida))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
