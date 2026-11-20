"""DT-13 (#267): al partir crear_app en routers, ninguna ruta puede quedar registrada dos veces
(FastAPI no avisa: la segunda queda escondida detrás de la primera)."""
from collections import Counter

from scripts.tesis.generar_docs import _app, _rutas


def test_cada_metodo_y_ruta_se_registra_una_sola_vez():
    pares = Counter((metodo, r.path) for r in _rutas(_app().routes) for metodo in r.methods)
    repetidas = [par for par, veces in pares.items() if veces > 1]
    assert repetidas == []
    assert len(pares) == 75  # catálogo de docs/tesis/catalogo-endpoints.md
