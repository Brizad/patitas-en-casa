"""Exportar en CSV y PDF anonimizados (RF-31, fase 5, #102).

Anonimizar no es solo quitar el nombre. De cada reporte se quita todo lo que permita llegar
a una persona o a una casa: la descripción (puede traer nombres o teléfonos), la dirección y
el GPS (se deja solo la comuna), la hora exacta (se deja el día) y el código de seguimiento
(con él se consulta el caso). Se cambia el código por un número de fila. Tampoco van
correos de veterinarios ni de rescatistas.

CSV seguro: una celda que empieza con =, +, - o @ se abre como fórmula en Excel («inyección
de CSV»); se antepone una comilla simple para que se muestre como texto.
"""
from __future__ import annotations

import csv
import io
from datetime import UTC

from app.documentos.pdf import generar_pdf
from app.dominio.modelos import Animal, DecisionTriaje, Reporte

COLUMNAS = ["fila", "dia", "comuna", "estado", "prioridad_sugerida", "prioridad_final",
            "ajustada", "minutos_hasta_confirmar", "version_modelo"]


def filas_anonimizadas(reportes: list[Reporte],
                       decisiones: dict[str, DecisionTriaje]) -> list[dict]:
    filas = []
    for n, r in enumerate(sorted(reportes, key=lambda x: x.creado_en), start=1):
        d = decisiones.get(r.codigo)
        filas.append({
            "fila": n, "dia": r.creado_en.astimezone(UTC).date().isoformat(),
            "comuna": r.ubicacion.comuna or "", "estado": r.estado.value,
            "prioridad_sugerida": d.prioridad_sugerida.value if d else
            (r.prioridad.value if r.prioridad else ""),
            "prioridad_final": d.prioridad_final.value if d else "",
            "ajustada": "" if d is None else ("si" if d.ajustada else "no"),
            "minutos_hasta_confirmar": "" if d is None else
            round((d.decidido_en - r.creado_en).total_seconds() / 60, 1),
            "version_modelo": r.version_modelo or ""})
    return filas


def _celda(valor) -> str:
    texto = str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@") else texto


def a_csv(filas: list[dict]) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(COLUMNAS)
    for fila in filas:
        escritor.writerow([_celda(fila[c]) for c in COLUMNAS])
    return salida.getvalue()


def resumen_pdf(indicadores: dict, generado: str) -> bytes:
    """Los indicadores de RF-30 en un PDF de una página, para informes (p. ej. Alcaldía)."""
    rep, ado = indicadores["reportes"], indicadores["adopciones"]
    lineas: list[str | tuple[str, int]] = [
        ("Patitas en Casa · Indicadores (anonimizados)", 16), f"Generado: {generado} (UTC)", "",
        ("Reportes", 13), f"Total: {rep['total']}",
        f"Por estado: {_lista(rep['por_estado'])}",
        f"Prioridad confirmada: {_lista(rep['por_prioridad_confirmada'])}",
        f"Minutos hasta confirmar (mediana): {rep['minutos_hasta_confirmar']['mediana']}", "",
        ("Refugios", 13)]
    lineas += [f"{r['nombre']}: {r['ocupados']}/{r['capacidad']} ({r['porcentaje']} %)"
               for r in indicadores["refugios"]]
    lineas += ["", ("Adopciones", 13), f"Aprobadas: {ado['aprobadas']}",
               f"Seguimientos: {_lista(ado['seguimientos'])}", "",
               "Sin datos personales: ni nombres, ni direcciones, ni correos (RF-31, Ley 1581)."]
    return generar_pdf(lineas)


def _lista(conteo: dict) -> str:
    return ", ".join(f"{k} {v}" for k, v in conteo.items()) or "sin datos"


COLUMNAS_FICHAS = ["id", "especie", "ingreso", "egreso", "motivo_egreso", "vacunado",
                   "esterilizado", "notas_clinicas"]


def fichas_csv(animales: list[tuple[Animal, int]]) -> str:
    """RF-31: fichas del refugio sin el texto de las notas (pueden nombrar personas): solo
    cuántas hay. Fechas por día."""
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(COLUMNAS_FICHAS)
    for a, notas in animales:
        escritor.writerow([_celda(v) for v in (
            a.id, a.especie.value,
            a.ingresado_en.astimezone(UTC).date().isoformat() if a.ingresado_en else "",
            a.egresado_en.astimezone(UTC).date().isoformat() if a.egresado_en else "",
            a.motivo_egreso.value if a.motivo_egreso else "",
            "si" if a.vacunado else "no", "si" if a.esterilizado else "no", notas)])
    return salida.getvalue()
