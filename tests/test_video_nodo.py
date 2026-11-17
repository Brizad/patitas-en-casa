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


# --- #231: el nodo instalado se pone al día solo; tu copia de desarrollo nunca se toca ---

GIT = shutil.which("git")
con_git = pytest.mark.skipif(GIT is None, reason="sin git")


def _git(carpeta: Path, *args: str) -> str:
    orden = [GIT, "-C", carpeta.as_posix(), "-c", "user.name=prueba",
             "-c", "user.email=prueba@localhost", "-c", "core.autocrlf=false", *args]
    return subprocess.run(orden, capture_output=True, text=True, check=True).stdout.strip()


def _nodo_instalado(tmp_path: Path) -> tuple[Path, Path]:
    """Un «GitHub» local con el script de arranque y un clon suyo marcado como el nodo."""
    origen, nodo = tmp_path / "origen", tmp_path / "patitas"
    (origen / "servicios" / "video").mkdir(parents=True)
    _git(origen, "init", "--quiet", "-b", "main")
    shutil.copy(CARPETA / "arrancar_nodo.sh", origen / "servicios" / "video")
    (origen / "servicios" / "video" / "requirements.txt").write_text("httpx\n", newline="\n")
    _git(origen, "add", "-A")
    _git(origen, "commit", "--quiet", "-m", "primera versión")
    subprocess.run([GIT, "clone", "--quiet", origen.as_uri(), nodo.as_posix()], check=True)
    (tmp_path / ".patitas-video").mkdir()
    marca = subprocess.run([BASH, "-c", 'cd "$1" && pwd', "_", nodo.as_posix()],
                           capture_output=True, text=True, check=True).stdout.strip()
    (tmp_path / ".patitas-video" / "carpeta").write_text(marca, newline="\n")
    return origen, nodo


def _arrancar_nodo(tmp_path: Path, nodo: Path, **extra: str) -> subprocess.CompletedProcess:
    entorno = {"PATH": os.environ.get("PATH", ""), "HOME": str(tmp_path),
               "PATITAS_PYTHON": _python_falso(tmp_path).as_posix(),
               "PATITAS_VIDEO_TOKEN": TOKEN, **extra}
    return subprocess.run([BASH, (nodo / "servicios/video/arrancar_nodo.sh").as_posix()],
                          input="", capture_output=True, text=True, env=entorno, timeout=60)


def _publicar(origen: Path, archivo: str, texto: str) -> str:
    (origen / archivo).write_text(texto, newline="\n")
    _git(origen, "add", "-A")
    _git(origen, "commit", "--quiet", "-m", f"cambia {archivo}")
    return _git(origen, "rev-parse", "HEAD")


def test_la_copia_de_desarrollo_nunca_se_actualiza_sola(tmp_path):
    """Sin la marca que deja instalar_nodo.sh el script no toca git (este repositorio)."""
    resultado = _arrancar(tmp_path, f"{TOKEN}\nn\n")
    assert "no se actualiza solo" in resultado.stdout and "con token" in resultado.stdout
    assert "Nodo actualizado" not in resultado.stdout


@con_git
def test_el_nodo_instalado_se_pone_al_dia_antes_de_trabajar(tmp_path):
    origen, nodo = _nodo_instalado(tmp_path)
    nuevo = _publicar(origen, "servicios/video/novedad.txt", "código nuevo\n")
    resultado = _arrancar_nodo(tmp_path, nodo)
    assert resultado.returncode == 0, resultado.stderr
    assert "Nodo actualizado" in resultado.stdout and "con token" in resultado.stdout
    assert _git(nodo, "rev-parse", "HEAD") == nuevo
    assert "args: -m pip" not in resultado.stdout  # las librerías no cambiaron


@con_git
def test_si_cambian_las_librerias_se_instalan(tmp_path):
    origen, nodo = _nodo_instalado(tmp_path)
    _publicar(origen, "servicios/video/requirements.txt", "httpx\nnumpy\n")
    assert "args: -m pip install -r" in _arrancar_nodo(tmp_path, nodo).stdout


@con_git
def test_lo_cambiado_a_mano_se_guarda_antes_de_actualizar(tmp_path):
    origen, nodo = _nodo_instalado(tmp_path)
    _publicar(origen, "servicios/video/novedad.txt", "código nuevo\n")
    (nodo / "servicios/video/copiado_a_mano.py").write_text("x = 1\n", newline="\n")
    resultado = _arrancar_nodo(tmp_path, nodo)
    assert "quedaron guardados" in resultado.stdout and "con token" in resultado.stdout
    assert "antes de actualizar el nodo" in _git(nodo, "stash", "list")


@con_git
def test_sin_red_o_sin_querer_actualizar_arranca_con_lo_que_tiene(tmp_path):
    origen, nodo = _nodo_instalado(tmp_path)
    _publicar(origen, "servicios/video/novedad.txt", "código nuevo\n")
    viejo = _git(nodo, "rev-parse", "HEAD")
    quieto = _arrancar_nodo(tmp_path, nodo, PATITAS_SIN_ACTUALIZAR="1")
    assert "con token" in quieto.stdout and _git(nodo, "rev-parse", "HEAD") == viejo
    shutil.rmtree(origen, ignore_errors=True)
    sin_red = _arrancar_nodo(tmp_path, nodo)
    assert "con GitHub: sigo" in sin_red.stdout and "con token" in sin_red.stdout


def test_sin_ffmpeg_avisa_que_no_habra_vista_previa(tmp_path):
    entorno = {"PATH": os.environ.get("PATH", ""), "HOME": str(tmp_path),
               "PATITAS_PYTHON": _python_falso(tmp_path).as_posix(),
               "PATITAS_VIDEO_TOKEN": TOKEN, "PATITAS_FFMPEG": "ffmpeg-que-no-existe"}
    salida = subprocess.run([BASH, (CARPETA / "arrancar_nodo.sh").as_posix()], input="",
                            capture_output=True, text=True, env=entorno, timeout=30).stdout
    assert "falta ffmpeg" in salida and "SIN vista previa" in salida and "con token" in salida


def test_el_instalador_deja_la_marca_que_permite_actualizarse():
    instalador = (CARPETA / "instalar_nodo.sh").read_text("utf-8")
    assert '> "$HOME/.patitas-video/carpeta"' in instalador and "ffmpeg" in instalador
