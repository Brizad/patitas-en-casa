"""Flujos de GitHub Actions que no deben despertar la base de Neon (#386).

Neon solo se suspende tras 5 min sin consultas; un sondeo que consulta la base cada 30 min la
mantenía despierta y agotó las horas gratis del mes. Se revisa el texto del YAML (sin PyYAML).
"""
from pathlib import Path

FLUJOS = Path(__file__).resolve().parent.parent / ".github" / "workflows"


def test_el_sondeo_corre_cada_6_horas():
    texto = (FLUJOS / "sondeo.yml").read_text(encoding="utf-8")
    assert '- cron: "0 */6 * * *"' in texto
    assert "*/30" not in texto


def test_el_sondeo_solo_pide_la_pwa_que_no_toca_la_base():
    texto = (FLUJOS / "sondeo.yml").read_text(encoding="utf-8")
    pedidos = [linea for linea in texto.splitlines() if "curl" in linea]
    assert pedidos and all("/app/" in linea for linea in pedidos)
    # GET /reportes/{codigo} consulta PostgreSQL: ya no se pide.
    assert not any("/reportes" in linea for linea in pedidos)
