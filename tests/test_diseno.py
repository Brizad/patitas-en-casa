"""Sistema de diseño único (#164): una hoja de estilo compartida por inicio, PWA y panel."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria

CSS = Path(__file__).resolve().parents[1] / "app" / "diseno" / "sistema.css"


@pytest.fixture
def c():
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def test_la_hoja_se_sirve_como_css_sin_sesion(c):
    r = c.get("/diseno/sistema.css")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")


def test_define_los_componentes_del_sistema():
    css = CSS.read_text(encoding="utf-8")
    for clase in ("ds-btn", "ds-btn--pri", "ds-tarjeta", "ds-tabla", "ds-insignia",
                  "ds-insignia--critica", "ds-insignia--alta", "ds-insignia--media",
                  "ds-insignia--baja", "ds-vacio", "ds-msg--error", "ds-msg--ok"):
        assert f".{clase}" in css, clase


def test_tiene_modo_oscuro_y_sin_recursos_externos():
    css = CSS.read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in css
    assert not re.search(r"https?://|@import", css)  # la CSP solo admite el propio servidor


def test_las_casillas_se_alinean_con_su_texto():
    css = CSS.read_text(encoding="utf-8")
    assert 'label:has(> input[type="checkbox"])' in css


def test_el_sistema_ofrece_formularios_en_rejilla():
    assert ".ds-form" in CSS.read_text(encoding="utf-8")


# --- Tokens compartidos del rediseño (#296): primitivos --pc-* y semánticos --ds-* mapeados. ---

def _tokens(bloque: str) -> dict[str, str]:
    return {k: v.strip() for k, v in re.findall(r"--([\w-]+):\s*([^;]+);", bloque)}


def _resolver(tokens: dict[str, str], nombre: str) -> str:
    valor = tokens[nombre]
    while (m := re.fullmatch(r"var\(--([\w-]+)\)", valor)):
        valor = tokens[m.group(1)]
    return valor


def _contraste(a: str, b: str) -> float:
    def luz(h):
        r, g, b_ = (int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b_)
    claro, oscuro = sorted((luz(a), luz(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def _temas():
    css = CSS.read_text(encoding="utf-8")
    claro, oscuro = css.split("@media (prefers-color-scheme: dark)", 1)
    base = _tokens(claro.split("/* Base", 1)[0])
    return base, {**base, **_tokens(oscuro.split("/* Base", 1)[0])}


TEXTO_SOBRE_FONDO = [
    ("ds-tinta", "ds-fondo"), ("ds-tinta", "ds-superficie"), ("ds-suave", "ds-fondo"),
    ("ds-suave", "ds-superficie"), ("ds-suave", "ds-marca-tenue"), ("ds-marca", "ds-fondo"),
    ("ds-marca", "ds-superficie"),
    ("ds-sobre-marca", "ds-marca"), ("ds-marca-fuerte", "ds-marca-tenue"),
    ("ds-tinta", "ds-marca-tenue"), ("ds-sobre-accion", "ds-accion"),
    ("ds-sobre-peligro", "ds-peligro"), ("ds-critica", "ds-critica-bg"),
    ("ds-alta", "ds-alta-bg"), ("ds-media", "ds-media-bg"), ("ds-baja", "ds-baja-bg"),
    ("ds-info", "ds-info-bg"), ("ds-tinta", "ds-realce")]


def test_primitivos_de_la_paleta():
    base, _ = _temas()
    for nombre, valor in (("pc-crema", "#ffffeb"), ("pc-tinta", "#1a1a1a"),
                          ("pc-lavanda", "#f0d7ff"), ("pc-bosque", "#034f46"),
                          ("pc-ascua", "#ffa946"), ("pc-piedra", "#e4e4d0")):
        assert base[nombre].lower() == valor, nombre
    assert base["pc-niebla"].lower() != "#8a8a80"  # oscurecido para llegar a 4,5:1


def test_los_nombres_ds_de_siempre_siguen_definidos():
    base, oscuro = _temas()
    for nombre in ("fondo", "superficie", "linea", "linea-fuerte", "tinta", "suave", "marca",
                   "marca-fuerte", "marca-tenue", "sobre-marca", "acento", "peligro",
                   "sobre-peligro", "fuente", "mono", "radio", "radio-lg", "e1", "e6", "t-xs",
                   "t-xl"):
        assert f"ds-{nombre}" in base and _resolver(oscuro, f"ds-{nombre}"), nombre


def test_contraste_aa_en_claro_y_oscuro():
    for nombre_tema, tema in zip(("claro", "oscuro"), _temas(), strict=True):
        for texto, fondo in TEXTO_SOBRE_FONDO:
            r = _contraste(_resolver(tema, texto), _resolver(tema, fondo))
            assert r >= 4.5, (nombre_tema, texto, fondo, round(r, 2))
        # Borde de los campos (WCAG 1.4.11): 3:1 contra la superficie.
        assert _contraste(_resolver(tema, "ds-linea-fuerte"), _resolver(tema, "ds-superficie")) >= 3


def test_titulos_en_serif():
    css = CSS.read_text(encoding="utf-8")
    assert "'EB Garamond'" in css and re.search(r"\.ds h1, \.ds h2 \{[^}]*var\(--pc-serif\)", css)


def test_componentes_con_la_forma_de_design_md():
    """#296, parte 2: borde de 2 px en lo que se toca, radio 12 en botones y campos, 32 en tarjetas
    y la acción principal en lavanda (--ds-accion)."""
    css = CSS.read_text(encoding="utf-8")
    base, _ = _temas()
    assert base["ds-radio"] == "12px"
    boton = re.search(r"\.ds-btn, :where\(\.ds\) button \{([^}]*)\}", css).group(1)
    campo = re.search(r"\.ds input, \.ds select, \.ds textarea \{([^}]*)\}", css).group(1)
    for regla in (boton, campo):
        assert "border: 2px solid var(--ds-linea-fuerte)" in regla
    principal = re.search(r"\.ds-btn--pri, \.ds button\.principal \{([^}]*)\}", css).group(1)
    assert "var(--ds-accion)" in principal and "var(--ds-sobre-accion)" in principal
    tarjeta = re.search(r"\.ds-tarjeta \{([^}]*)\}", css).group(1)
    assert "var(--pc-radio-tarjeta)" in tarjeta


def test_el_panel_no_fija_colores_y_sus_pestanas_no_dependen_del_color():
    """#300: los estilos propios del panel usan solo tokens; la pestaña actual del panel se
    marca con el fondo invertido (tinta), además de aria-current."""
    panel = (CSS.parents[2] / "panel" / "src" / "estilos.css").read_text(encoding="utf-8")
    reglas = re.sub(r"/\*.*?\*/", "", panel, flags=re.S)  # sin comentarios (citan issues: #300)
    assert len(reglas) > 500 and not re.search(r"#[0-9a-fA-F]{3,6}\b", reglas)
    css = CSS.read_text(encoding="utf-8")
    actual = re.search(r'\.ds-pestanas \[aria-current="page"\][^{]*\{([^}]*)\}', css).group(1)
    assert "background: var(--ds-tinta)" in actual


def test_la_prioridad_se_distingue_por_forma_ademas_del_color():
    """#302 (WCAG 1.4.1): cada insignia de prioridad tiene una forma propia, y en la cola la fila
    crítica y la alta llevan una barra lateral de distinto grosor. Sin sombras en el panel."""
    css = CSS.read_text(encoding="utf-8")
    formas = {p: re.search(rf"\.ds-insignia--{p}::before \{{([^}}]*)\}}", css) for p in
              ("critica", "alta", "media", "baja")}
    assert all(formas.values()), formas
    assert len({f.group(1) for f in formas.values()}) == 4  # cuatro formas distintas
    panel = (CSS.parents[2] / "panel" / "src" / "estilos.css").read_text(encoding="utf-8")
    critica = re.search(r"\.item--critica \{([^}]*)\}", panel).group(1)
    alta = re.search(r"\.item--alta \{([^}]*)\}", panel).group(1)
    assert "border-left-width: 8px" in critica and "border-left-width: 4px" in alta
    assert "box-shadow" not in panel


def test_rescatista_prioridad_y_comunas_sin_depender_del_color():
    """#303: oferta crítica con barra de 8 px y alta de 4 px; la comuna elegida se invierte."""
    panel = (CSS.parents[2] / "panel" / "src" / "estilos.css").read_text(encoding="utf-8")
    assert "border-left-width: 8px" in re.search(r"\.oferta--critica \{([^}]*)\}", panel).group(1)
    assert "border-left-width: 4px" in re.search(r"\.oferta--alta \{([^}]*)\}", panel).group(1)
    elegida = re.search(r"label\.comuna:has\(input:checked\) \{([^}]*)\}", panel).group(1)
    assert "background: var(--ds-tinta)" in elegida


def test_coordinador_cifras_en_serif_y_archivo_con_forma_de_boton():
    """#304: las cifras clave van en serif grande y el botón «Elegir archivo» tiene la forma del
    sistema (borde de 2 px), en la PWA y en el panel."""
    panel = (CSS.parents[2] / "panel" / "src" / "estilos.css").read_text(encoding="utf-8")
    assert "var(--pc-serif)" in re.search(r"\.kpi dd \{([^}]*)\}", panel).group(1)
    assert "border: 2px solid" in re.search(r"\.barra-ocupacion \{([^}]*)\}", panel).group(1)
    archivo = re.search(r"::file-selector-button \{([^}]*)\}", CSS.read_text(encoding="utf-8"))
    assert archivo and "border: 2px solid var(--ds-linea-fuerte)" in archivo.group(1)
