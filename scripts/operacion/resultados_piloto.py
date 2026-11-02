"""Resultados del piloto de usabilidad (RNF-06, #197).

Lee el CSV con un participante por fila (docs/piloto/plantilla.csv) y calcula:
- el % de participantes que envió el reporte en 90 s o menos (meta: 80 % o más);
- el puntaje SUS promedio de 0 a 100 (meta: 70 o más).

    python scripts/operacion/resultados_piloto.py docs/piloto/mis_resultados.csv

Las filas sin datos (la plantilla trae filas vacías) se ignoran. Una fila a medias o con
valores fuera de rango es un error que nombra al participante: mejor corregir que promediar mal.
Guía de la sesión: docs/aprende/piloto.md.
"""
from __future__ import annotations

import csv
import io
import sys
from dataclasses import dataclass
from pathlib import Path

META_SEGUNDOS = 90
META_PORCENTAJE = 80
META_SUS = 70
PREGUNTAS = 10


@dataclass(frozen=True)
class Resultado:
    participantes: int
    cumplen_tiempo: int
    sus_promedio: float

    @property
    def porcentaje_tiempo(self) -> float:
        return 100 * self.cumplen_tiempo / self.participantes

    @property
    def cumple_tiempo(self) -> bool:
        return self.porcentaje_tiempo >= META_PORCENTAJE

    @property
    def cumple_sus(self) -> bool:
        return self.sus_promedio >= META_SUS


def puntaje_sus(respuestas: list[int]) -> float:
    """SUS de una persona: ítems impares (r-1), pares (5-r), suma por 2,5 → 0 a 100."""
    if len(respuestas) != PREGUNTAS or any(not 1 <= r <= 5 for r in respuestas):
        raise ValueError(f"el SUS pide {PREGUNTAS} respuestas enteras de 1 a 5")
    suma = sum((r - 1) if i % 2 == 0 else (5 - r) for i, r in enumerate(respuestas))
    return suma * 2.5


def _entero(valor: str, nombre: str, quien: str) -> int:
    try:
        return int(valor.strip())
    except ValueError:
        raise ValueError(f"{quien}: «{nombre}» debe ser un número entero, no «{valor}»") from None


def calcular(texto_csv: str) -> Resultado:
    columnas_sus = [f"sus_{i}" for i in range(1, PREGUNTAS + 1)]
    cumplen = 0
    puntajes: list[float] = []
    for fila in csv.DictReader(io.StringIO(texto_csv)):
        quien = (fila.get("participante") or "").strip() or "fila sin nombre"
        celdas = [fila.get("segundos"), *(fila.get(c) for c in columnas_sus)]
        if all(not (c or "").strip() for c in celdas):
            continue  # fila de la plantilla sin llenar
        if any(not (c or "").strip() for c in celdas):
            raise ValueError(f"{quien}: faltan datos (tiempo y las {PREGUNTAS} respuestas)")
        segundos = _entero(fila["segundos"], "segundos", quien)
        if segundos <= 0:
            raise ValueError(f"{quien}: «segundos» debe ser mayor que 0")
        try:
            puntajes.append(puntaje_sus([_entero(fila[c], c, quien) for c in columnas_sus]))
        except ValueError as error:
            raise ValueError(f"{quien}: {error}") from None
        cumplen += segundos <= META_SEGUNDOS
    if not puntajes:
        raise ValueError("no hay participantes con datos en el archivo")
    return Resultado(len(puntajes), cumplen, sum(puntajes) / len(puntajes))


def informe(r: Resultado) -> str:
    def veredicto(ok: bool) -> str:
        return "CUMPLE" if ok else "NO CUMPLE"

    return "\n".join([
        f"Participantes: {r.participantes}",
        f"Reportan en {META_SEGUNDOS} s o menos: {r.cumplen_tiempo} de {r.participantes} "
        f"({r.porcentaje_tiempo:.0f} %) — meta {META_PORCENTAJE} %: {veredicto(r.cumple_tiempo)}",
        f"Puntaje SUS promedio: {r.sus_promedio:.1f} — meta {META_SUS}: "
        f"{veredicto(r.cumple_sus)}",
    ])


def main(argumentos: list[str]) -> int:
    if len(argumentos) != 1:
        print("Uso: python scripts/operacion/resultados_piloto.py <archivo.csv>")
        return 2
    try:
        texto = Path(argumentos[0]).read_text(encoding="utf-8-sig")
        print(informe(calcular(texto)))
    except (OSError, ValueError) as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
