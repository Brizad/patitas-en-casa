"""Reglas de dependencia comprobadas en cada ejecución (II-03, #63).

Las reglas de negocio no deben conocer el framework web, la base de datos ni el correo: así se
pueden probar en memoria y cambiar un adaptador sin tocarlas (principio P-04 del DAD, DIP).
"""
import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
INFRAESTRUCTURA = ("fastapi", "starlette", "sqlalchemy", "psycopg", "smtplib", "alembic",
                   "app.api", "app.bd", "app.notificaciones.correo")

# Módulos con reglas de negocio o casos de uso (sin adaptadores).
NUCLEO = ["dominio/modelos.py", "avisos/modelos.py", "avisos/repositorio.py",
          "avisos/procesador.py", "reportes/confirmacion.py", "reportes/descarte.py",
          "reportes/duplicados.py",
          "reportes/servicio.py",
          "rescates/servicio.py", "triaje/clasificador.py", "triaje/servicio.py",
          "triaje/modelo.py", "triaje/combinado.py", "triaje/video.py",
          "cupos/servicio.py", "cupos/fichas.py", "adopciones/modelos.py",
          "adopciones/repositorio.py", "adopciones/servicio.py",
          "adopciones/reglas.py", "adopciones/compromiso.py", "documentos/pdf.py",
          "adopciones/compatibilidad.py", "adopciones/asignacion.py",
          "bitacora/repositorio.py"]


def importaciones(ruta: Path) -> set[str]:
    nombres = set()
    for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
    return nombres


def prohibidas(ruta: Path) -> list[str]:
    return sorted(n for n in importaciones(ruta)
                  if any(n == p or n.startswith(p + ".") for p in INFRAESTRUCTURA))


@pytest.mark.parametrize("modulo", NUCLEO)
def test_el_nucleo_no_importa_infraestructura(modulo):
    assert prohibidas(APP / modulo) == []


def test_el_procesador_solo_conoce_la_excepcion_del_canal_no_el_smtp():
    """El procesador envía a través del puerto (entregar); no importa smtplib ni SQLAlchemy."""
    nombres = importaciones(APP / "avisos" / "procesador.py")
    assert not {"smtplib", "sqlalchemy"} & {n.split(".")[0] for n in nombres}


def test_la_regla_detecta_una_importacion_prohibida(tmp_path):
    """La comprobación misma se prueba: si alguien importa SQLAlchemy en el núcleo, falla."""
    falso = tmp_path / "modulo.py"
    falso.write_text("from sqlalchemy import select\nimport app.dominio.modelos\n")
    assert prohibidas(falso) == ["sqlalchemy"]
