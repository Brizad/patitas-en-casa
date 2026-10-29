"""Servidor local EN MEMORIA con los datos de demostración (#147).

Sirve para medir la accesibilidad (`revisar.mjs`) y tomar las capturas del manual sin tocar
PostgreSQL ni Render. Las cuentas son las de `app/demo.py` (dominio inventado
demo.patitas.co); su contraseña se lee de PATITAS_DEMO_CONTRASENA y nunca está en el código.

Uso: PATITAS_DEMO_CONTRASENA=... python scripts/accesibilidad/servidor_demo.py [puerto]
"""
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uvicorn  # noqa: E402

from app.api.main import crear_app  # noqa: E402
from app.cupos.repositorio import RepositorioCuposEnMemoria  # noqa: E402
from app.dominio.modelos import Refugio  # noqa: E402
from app.reportes.repositorio import RepositorioEnMemoria  # noqa: E402
from app.seguridad.cifrado import Cifrador  # noqa: E402
from app.seguridad.tokens import EmisorTokens  # noqa: E402
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria  # noqa: E402


def crear() -> object:
    contrasena = os.environ.get("PATITAS_DEMO_CONTRASENA")
    if not contrasena:
        raise SystemExit("Falta PATITAS_DEMO_CONTRASENA (cualquier valor de 12 caracteres o más).")
    # Claves de un solo uso: el servidor vive en memoria y se borra al cerrarlo.
    return crear_app(RepositorioEnMemoria(),
                     RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
                     repositorio_usuarios=RepositorioUsuariosEnMemoria(),
                     emisor_tokens=EmisorTokens(secrets.token_urlsafe(48)),
                     revisar_escalamientos_cada_s=None, procesar_avisos_cada_s=None,
                     contrasena_demo=contrasena,
                     cifrador=Cifrador(secrets.token_urlsafe(48)))


if __name__ == "__main__":
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    uvicorn.run(crear(), host="127.0.0.1", port=puerto, log_level="warning")
