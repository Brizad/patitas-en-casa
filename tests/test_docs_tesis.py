"""#243: la documentación de tesis que sale del código se puede regenerar y está completa."""
from fastapi.routing import APIRoute

from app.bd import esquema
from scripts.tesis import generar_docs as g


def test_el_catalogo_trae_todas_las_rutas_con_quien_y_codigos():
    catalogo = g.generar_catalogo()
    rutas = g._rutas(g._app().routes)
    filas = [linea for linea in catalogo.splitlines() if linea.startswith("| ") and "`/" in linea]
    assert len(filas) == sum(len(r.methods) for r in rutas if isinstance(r, APIRoute))
    assert "| POST | `/reportes` | público | 201, 422, 429 |" in catalogo
    assert "| POST | `/refugio/ingresos` | coordinador | 201, 401, 403," in catalogo
    assert "`/video/trabajos/{id_}/vista` | trabajador de video" in catalogo


def test_el_diccionario_y_el_er_traen_todas_las_tablas():
    diccionario, er = g.generar_diccionario(), g.generar_er()
    for tabla in esquema.metadata.tables:
        assert f"## `{tabla}`" in diccionario
        assert f"  {tabla} {{" in er
    assert "TIMESTAMP WITH TIME ZONE" in diccionario
    assert 'reportes ||--o{ rescates : "reporte_codigo"' in er
