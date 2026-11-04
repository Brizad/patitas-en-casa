"""#250: objetivos táctiles de 44 px o más y mensajes del ciudadano sin códigos internos.

La revisión completa en el navegador (360, 768 y 1440 px, claro y oscuro) la hace
scripts/accesibilidad/responsive.mjs; aquí se protege lo que corrigió.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SISTEMA = (RAIZ / "app" / "diseno" / "sistema.css").read_text(encoding="utf-8")
PANEL = (RAIZ / "panel" / "src" / "estilos.css").read_text(encoding="utf-8")


def alto_minimo(css: str, selector: str) -> int:
    regla = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert regla, f"no está la regla {selector}"
    return int(re.search(r"min-height:\s*(\d+)px", regla.group(1)).group(1))


def test_botones_chicos_enlaces_de_salto_y_casillas_miden_44_px():
    assert alto_minimo(SISTEMA, ".ds-btn--chico") >= 44
    assert alto_minimo(SISTEMA, ".ds .ds-saltar") >= 44
    assert alto_minimo(SISTEMA, '.ds label:has(> input[type="checkbox"]), '
                                '.ds label:has(> input[type="radio"])') >= 44


def test_botones_con_aspecto_de_enlace_y_casillas_del_panel_miden_44_px():
    assert alto_minimo(PANEL, "button.enlace") >= 44
    assert alto_minimo(PANEL, ".en-linea") >= 44


def test_la_pwa_no_le_muestra_codigos_internos_al_ciudadano():
    js = (RAIZ / "app" / "pwa" / "reportar.js").read_text(encoding="utf-8")
    textos = re.findall(r"'([^']*)'", js)
    assert not [t for t in textos if re.search(r"\((RN|RF|RNF)-\d+\)", t)]
