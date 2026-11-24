"""scripts/dev/arrancar_local.ps1 (#398): arranque local en Windows. Se revisa el texto (el CI
corre en Linux); la prueba real en Windows está en docs/aprende/desarrollo-local.md."""
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "dev" / "arrancar_local.ps1"


def _texto() -> str:
    return SCRIPT.read_text(encoding="utf-8-sig")


def test_tiene_bom_para_que_powershell_5_lea_bien_las_tildes():
    assert SCRIPT.read_bytes().startswith(b"\xef\xbb\xbf")


def test_hace_los_pasos_en_orden():
    texto = _texto()
    texto = texto[texto.index("$ErrorActionPreference"):]  # el código, sin la ayuda de arriba
    pasos = ["Test-Path $ArchivoEnv", "Copy-Item .env.example .env", "alembic upgrade head",
             "npm ci", "npm run build", '$env:PATITAS_DEMO_ACTIVA = "true"',
             '"--factory", "app.api.main:crear_app"']
    posiciones = [texto.index(paso) for paso in pasos]
    assert posiciones == sorted(posiciones)
    assert '"--reload"' in texto and "$Puerto = 8000" in texto


def test_nunca_muestra_contrasenas_ni_claves():
    for linea in _texto().splitlines():
        if "Write-Host" in linea:
            for variable in ("POSTGRES_PASSWORD", "PATITAS_JWT_SECRETO", "PATITAS_CLAVE_DATOS",
                             "PATITAS_DEMO_CONTRASENA", "$valor"):
                assert f"$env:{variable}" not in linea and "$valor" not in linea, linea
