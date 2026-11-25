"""Parte 7c: producción dice qué commit corre (cabecera X-Version-Commit), para que «Verificar
despliegue» confirme el commit y no solo la versión de pyproject, que no cambia en cada PR."""
from pathlib import Path

from app.api import middlewares
from tests.test_inicio import c  # noqa: F401  (fixture de la app en memoria)

FLUJO = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "deploy.yml"


def test_con_el_commit_de_render_la_respuesta_lo_dice(c, monkeypatch):  # noqa: F811
    monkeypatch.setattr(middlewares, "COMMIT_DESPLEGADO", "abc123def456")
    assert c.get("/app/").headers["x-version-commit"] == "abc123def456"


def test_sin_la_variable_no_se_inventa_nada(c, monkeypatch):  # noqa: F811
    monkeypatch.setattr(middlewares, "COMMIT_DESPLEGADO", "")
    assert "x-version-commit" not in c.get("/app/").headers


def test_verificar_despliegue_espera_el_commit_unido():
    texto = FLUJO.read_text(encoding="utf-8")
    assert "X-Version-Commit" in texto or "x-version-commit" in texto
    assert "github.event.workflow_run.head_sha" in texto
