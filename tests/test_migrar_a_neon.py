"""Script de migración de Render a Neon (#154): sin red ni cuentas, solo su lógica."""
import importlib.util
import sys
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "scripts" / "operacion" / "migrar_a_neon.py"
spec = importlib.util.spec_from_file_location("migrar_a_neon", RUTA)
migrar = importlib.util.module_from_spec(spec)
sys.modules["migrar_a_neon"] = migrar  # dataclass lo busca por su nombre
spec.loader.exec_module(migrar)

# Direcciones INVENTADAS con el formato que muestran Render y Neon.
RENDER = "postgresql://patitas:clave-de-render@dpg-ejemplo-a.oregon-postgres.render.com/patitas"
NEON = ("postgresql://neondb_owner:clave%40neon@ep-ejemplo-123.us-west-2.aws.neon.tech/"
        "neondb?sslmode=require&channel_binding=require")


def test_lee_la_direccion_de_render():
    c = migrar.leer_url(RENDER)
    assert (c.host, c.puerto, c.usuario, c.base, c.sslmode) == (
        "dpg-ejemplo-a.oregon-postgres.render.com", 5432, "patitas", "patitas", None)
    assert c.contrasena == "clave-de-render"


def test_lee_la_direccion_de_neon_con_tls_y_caracteres_escapados():
    c = migrar.leer_url(NEON)
    assert c.contrasena == "clave@neon" and c.base == "neondb" and c.sslmode == "require"


@pytest.mark.parametrize("mala", ["mysql://u:c@h/b", "postgresql://u:c@h/", "postgresql://h/b",
                                  "no es una url"])
def test_rechaza_direcciones_incompletas(mala):
    with pytest.raises(ValueError):
        migrar.leer_url(mala)


def test_la_contrasena_va_en_el_entorno_y_nunca_en_las_variables_de_render():
    c = migrar.leer_url(NEON)
    assert c.entorno()["PGPASSWORD"] == "clave@neon"
    assert c.entorno()["PGSSLMODE"] == "require"
    render = c.variables_render()
    assert render == {"POSTGRES_HOST": "ep-ejemplo-123.us-west-2.aws.neon.tech",
                      "POSTGRES_PORT": "5432", "POSTGRES_USER": "neondb_owner",
                      "POSTGRES_DB": "neondb", "POSTGRES_SSLMODE": "require"}
    assert "clave@neon" not in str(render)


def test_la_contrasena_no_aparece_en_la_linea_de_comandos(monkeypatch):
    vistos = {}

    def falso(comando, env, **_):
        vistos["comando"], vistos["env"] = comando, env
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(migrar.subprocess, "run", falso)
    migrar.ejecutar(["pg_dump", "--file", "x"], migrar.leer_url(NEON))
    assert "clave@neon" not in " ".join(vistos["comando"])
    assert vistos["env"]["PGPASSWORD"] == "clave@neon"


def test_compara_las_filas_tabla_por_tabla():
    origen = {"reportes": 7, "usuarios": 6, "bitacora": 40}
    assert migrar.diferencias(origen, dict(origen)) == []
    problemas = migrar.diferencias(origen, {"reportes": 7, "usuarios": 5})
    assert problemas == ["bitacora: Render 40, Neon no existe", "usuarios: Render 6, Neon 5"]


def test_siempre_exige_tls_sin_cambiar_lo_que_ya_venia():
    assert migrar.con_tls(migrar.leer_url(RENDER)).sslmode == "require"
    assert migrar.con_tls(migrar.leer_url(NEON + "x")).sslmode == "require"
