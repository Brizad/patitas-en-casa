"""Complejidad de las fábricas de rutas: Ruff exige C901 ≤ 10 y la única salida era un
`# noqa: C901`. Esta lista solo puede encogerse: quien saque una fábrica de aquí ya no puede
volver a silenciar la regla, y nadie agrega un `noqa` nuevo sin que esta prueba lo diga."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# Fábricas que todavía silencian la regla (deuda conocida; ver PLAN_CIERRE.md, trabajo 4c).
PENDIENTES = {"app/api/video.py"}


def test_solo_las_fabricas_pendientes_silencian_la_complejidad():
    con_noqa = {ruta.relative_to(RAIZ).as_posix()
                for carpeta in ("app", "servicios", "scripts")
                for ruta in (RAIZ / carpeta).rglob("*.py")
                if "noqa: C901" in ruta.read_text(encoding="utf-8")}
    assert con_noqa <= PENDIENTES, f"noqa: C901 nuevo en {sorted(con_noqa - PENDIENTES)}"
    assert PENDIENTES <= con_noqa, (
        f"Ya no silencian la regla: sácalas de PENDIENTES: {sorted(PENDIENTES - con_noqa)}")


def test_las_rutas_de_adopcion_ya_no_silencian_la_complejidad():
    assert "noqa" not in (RAIZ / "app/api/rutas_adopciones.py").read_text(encoding="utf-8")
