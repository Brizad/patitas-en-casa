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


RESTAURAR = FLUJOS / "restaurar-a-neon-nuevo.yml"


def test_restaurar_solo_se_lanza_a_mano_y_pide_confirmacion():
    texto = RESTAURAR.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in texto and "schedule:" not in texto
    assert '"$CONFIRMAR" != "RESTAURAR"' in texto


def test_restaurar_falla_claro_sin_el_secreto_y_no_imprime_la_cadena():
    texto = RESTAURAR.read_text(encoding="utf-8")
    assert "Falta el secreto NEON_DATABASE_URL_NUEVA" in texto
    lineas = texto.splitlines()
    # La cadena solo viaja como variable de entorno; ningún echo ni printf la muestra.
    assert not [linea for linea in lineas
                if ("echo" in linea or "printf" in linea) and "$NUEVA" in linea]
    assert "set -x" not in texto


def test_restaurar_descifra_igual_que_el_respaldo_y_verifica_la_restauracion():
    texto = RESTAURAR.read_text(encoding="utf-8")
    respaldo = (FLUJOS / "respaldo.yml").read_text(encoding="utf-8")
    cifrado = "-aes-256-cbc -pbkdf2 -iter 600000"
    assert cifrado in texto and cifrado in respaldo
    assert 'PG_VERSION: "18"' in texto
    assert "--exit-on-error" in texto and "alembic_version" in texto
    assert "no se restaura encima" in texto  # nunca sobre una base con tablas
