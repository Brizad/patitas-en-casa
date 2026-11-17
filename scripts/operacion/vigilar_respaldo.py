"""Vigilancia del respaldo diario (RNF-15). Lo usa `.github/workflows/respaldo.yml`.

    python -m scripts.operacion.vigilar_respaldo version <server_version_num> <PG_VERSION>
    python -m scripts.operacion.vigilar_respaldo respaldos artefactos.json

- `version`: pg_dump solo respalda servidores de su versión o anteriores. Si Neon se actualiza
  (pasó en #210: pg_dump 17 contra PostgreSQL 18), el flujo se detiene antes de la copia y dice
  qué línea cambiar.
- `respaldos`: lee la lista de artefactos del repositorio (API de GitHub) y alerta si el
  respaldo más reciente que aún se puede descargar tiene más de 26 horas (uno al día, más dos
  horas de margen).

Cuando alerta sale con código 1 y un mensaje `::error::`, que GitHub muestra en rojo y avisa
por correo al dueño del repositorio. No lee ni imprime ningún secreto.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

MAX_HORAS = 26
PREFIJO = "respaldo-"


def revisar_version(servidor_num: str, cliente: str) -> tuple[bool, str]:
    """`servidor_num` es la respuesta de SHOW server_version_num (180001 = 18.1)."""
    try:
        mayor_servidor, mayor_cliente = int(servidor_num.strip()) // 10000, int(cliente)
    except ValueError:
        return False, ("No se pudo leer la versión del servidor de Neon (respondió "
                       f"«{servidor_num.strip()[:20]}»). Revisa el secreto NEON_DATABASE_URL.")
    if mayor_servidor > mayor_cliente:
        return False, (f"Neon corre PostgreSQL {mayor_servidor} y este flujo usa pg_dump "
                       f"{mayor_cliente}: la copia fallaría. En .github/workflows/respaldo.yml "
                       f'cambia PG_VERSION: "{mayor_cliente}" por PG_VERSION: "{mayor_servidor}".')
    return True, f"Servidor PostgreSQL {mayor_servidor}, pg_dump {mayor_cliente}: compatibles."


def revisar_respaldos(artefactos: list[dict], ahora: datetime) -> tuple[bool, str]:
    fechas = [datetime.fromisoformat(a["created_at"].replace("Z", "+00:00"))
              for a in artefactos
              if a.get("name", "").startswith(PREFIJO) and not a.get("expired")]
    if not fechas:
        return False, ("No hay ningún respaldo guardado. Revisa los secretos NEON_DATABASE_URL "
                       "y RESPALDO_CLAVE y lanza «Respaldo diario» a mano "
                       "(docs/aprende/respaldo.md).")
    ultimo = max(fechas)
    horas = int((ahora - ultimo).total_seconds() // 3600)
    if horas > MAX_HORAS:
        return False, (f"El último respaldo exitoso es del {ultimo:%Y-%m-%d %H:%M} UTC: hace "
                       f"{horas} h (más de {MAX_HORAS}). Mira por qué falló «Respaldo diario» "
                       "y lánzalo a mano (docs/aprende/respaldo.md).")
    return True, f"Último respaldo: {ultimo:%Y-%m-%d %H:%M} UTC, hace {horas} h."


def main(argumentos: list[str] | None = None, ahora: datetime | None = None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    if len(argumentos) == 3 and argumentos[0] == "version":
        bien, mensaje = revisar_version(argumentos[1], argumentos[2])
    elif len(argumentos) == 2 and argumentos[0] == "respaldos":
        datos = json.loads(Path(argumentos[1]).read_text("utf-8"))
        bien, mensaje = revisar_respaldos(datos.get("artifacts", []), ahora or datetime.now(UTC))
    else:
        print(__doc__)
        return 2
    print(mensaje if bien else f"::error::{mensaje}")
    return 0 if bien else 1


if __name__ == "__main__":
    raise SystemExit(main())
