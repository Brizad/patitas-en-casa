#!/usr/bin/env bash
# Pruebas de mutación (#272) con mutmut 3 sobre las reglas de negocio. mutmut no corre en
# Windows: usa WSL2 (o Linux). Tarda unos 14 minutos, por eso NO está en el CI.
#   bash scripts/operacion/mutacion.sh            # crea ~/patitas-mut, instala y corre
#   cd ~/patitas-mut && mutmut browse             # ver cada mutante sobreviviente
# Las pruebas de PostgreSQL se omiten (sin base): los repositorios PostgreSQL salen «no tests».
set -euo pipefail
ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESTINO="${MUTACION_DESTINO:-$HOME/patitas-mut}"
PYTHON="${MUTACION_PYTHON:-python3.12}"
mkdir -p "$DESTINO" && cd "$ORIGEN"
tar --exclude=__pycache__ -cf - app tests scripts servicios migraciones pyproject.toml \
    alembic.ini requirements.txt requirements-dev.txt | (cd "$DESTINO" && tar xf -)
cd "$DESTINO" && rm -f .env  # nunca credenciales en la copia
[ -d .venv-mut ] || "$PYTHON" -m venv .venv-mut
. .venv-mut/bin/activate
pip install -q -r requirements-dev.txt mutmut==3.3.1
# Mutar solo app/triaje, app/cupos, app/rescates y app/adopciones/reglas.py; las pruebas que
# leen el panel o docs/ no aplican aquí.
excluir=$(find app -name "*.py" | grep -vE "^app/(triaje|cupos|rescates)/|^app/adopciones/reglas.py$" \
          | sed 's/.*/"&"/' | paste -sd, -)
pruebas=$(grep -lE "app\.(triaje|cupos|rescates)|app\.adopciones\.(reglas|servicio)|from tests.test_api import|app.api.main import" tests/test_*.py \
          | grep -vE "objetivos|tablas_celular|docs_tesis|pwa|inicio|accesib|diseno|panel" | sed 's/.*/"&"/' | paste -sd, -)
python - "$excluir" "$pruebas" <<'PY'
import pathlib, sys
p = pathlib.Path("pyproject.toml"); s = p.read_text()
s = s.split("[tool.mutmut]")[0] + f"""[tool.mutmut]
paths_to_mutate = ["app/"]
do_not_mutate = [{sys.argv[1]}]
tests_dir = [{sys.argv[2]}]
also_copy = ["scripts/", "servicios/", "migraciones/", "alembic.ini"]
pytest_add_cli_args = ["-p", "no:cacheprovider", "-q", "-m", "not postgres"]
"""
p.write_text(s)
PY
rm -rf mutants && mutmut run --max-children "$(nproc)" || true
mutmut results --all true | awk -F': ' '{print $2}' | sort | uniq -c
