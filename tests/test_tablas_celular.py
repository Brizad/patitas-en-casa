"""#252: en el celular las tablas del rescatista y del veterinario se leen sin deslizar de lado."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_el_sistema_de_diseno_apila_las_tablas_en_pantallas_angostas():
    css = (RAIZ / "app" / "diseno" / "sistema.css").read_text(encoding="utf-8")
    consulta = re.search(r"@media \(max-width: 600px\) \{(.*?)\n\}", css, re.S)
    assert consulta and "ds-tabla--tarjetas td::before" in consulta.group(1)
    assert "attr(data-etiqueta)" in consulta.group(1)


def test_cada_celda_de_mis_rescates_y_del_historial_tiene_su_etiqueta():
    for archivo, columnas in (("MisRescates.tsx", 5), ("Historial.tsx", 7)):
        tsx = (RAIZ / "panel" / "src" / archivo).read_text(encoding="utf-8")
        assert "ds-tabla--tarjetas" in tsx
        cuerpo = tsx[tsx.index("<tbody>"):tsx.index("</tbody>")]
        assert cuerpo.count("<td") == cuerpo.count("data-etiqueta=") == columnas
