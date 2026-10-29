"""Scripts del nodo de video (#125): sintaxis y que el token nunca se muestre."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

CARPETA = Path(__file__).resolve().parents[1] / "servicios" / "video"
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="sin bash")
TOKEN = "token-secreto-de-prueba-123"


def _python_falso(tmp_path: Path) -> Path:
    """Reemplaza al Python del entorno: solo dice si recibió el token y con qué argumentos."""
    falso = tmp_path / "python"
    falso.write_text(
        '#!/usr/bin/env bash\n'
        'if [ -n "$PATITAS_VIDEO_TOKEN" ]; then echo "con token"; else echo "sin token"; fi\n'
        'echo "args: $*"\n',
        newline="\n",
    )
    falso.chmod(0o755)
    return falso


def _arrancar(tmp_path: Path, entrada: str, *args: str) -> subprocess.CompletedProcess:
    entorno = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "PATITAS_PYTHON": _python_falso(tmp_path).as_posix(),
    }
    return subprocess.run(
        [BASH, (CARPETA / "arrancar_nodo.sh").as_posix(), *args],
        input=entrada, capture_output=True, text=True, env=entorno, timeout=30,
    )


@pytest.mark.parametrize("script", ["instalar_nodo.sh", "arrancar_nodo.sh"])
def test_los_scripts_tienen_sintaxis_valida_y_fin_de_linea_unix(script):
    ruta = CARPETA / script
    assert b"\r\n" not in ruta.read_bytes()
    assert subprocess.run([BASH, "-n", ruta.as_posix()]).returncode == 0


def test_pide_el_token_sin_mostrarlo_y_se_lo_pasa_al_trabajador(tmp_path):
    resultado = _arrancar(tmp_path, f"{TOKEN}\nn\n")
    assert resultado.returncode == 0, resultado.stderr
    assert "con token" in resultado.stdout
    assert TOKEN not in resultado.stdout + resultado.stderr
    assert not (tmp_path / ".patitas-video" / "token").exists()


def test_guarda_el_token_solo_si_se_pide(tmp_path):
    _arrancar(tmp_path, f"{TOKEN}\ns\n")
    guardado = tmp_path / ".patitas-video" / "token"
    assert guardado.read_text() == TOKEN
    segunda = _arrancar(tmp_path, "")  # la segunda vez no pregunta
    assert "con token" in segunda.stdout and "Pega el token" not in segunda.stdout


def test_sin_token_no_arranca(tmp_path):
    resultado = _arrancar(tmp_path, "\n")
    assert resultado.returncode == 1
    assert "args:" not in resultado.stdout


def test_un_video_suelto_no_pide_token(tmp_path):
    resultado = _arrancar(tmp_path, "", "--video", "perro.mp4")
    assert "Pega el token" not in resultado.stdout
    assert "args: -m patitas_video.trabajador --video perro.mp4" in resultado.stdout
