"""Genera la documentación de tesis que sale del código, para que nunca se desactualice.

Uso (desde la raíz del repositorio):  python -m scripts.tesis.generar_docs

Escribe en docs/tesis/:
- er.md: diagrama entidad-relación (Mermaid) desde las tablas de app/bd/esquema.py.
- diccionario-datos.md: cada tabla y columna con tipo, nulos, claves, restricciones y el
  comentario que tiene en esquema.py.
- catalogo-endpoints.md: cada ruta de la API con quién puede usarla (leído de exigir_rol),
  los códigos de respuesta que la ruta lanza y los requisitos que cita su código.

No necesita PostgreSQL: la app se arma con repositorios en memoria y solo se leen sus rutas.
"""
from __future__ import annotations

import ast
import inspect
import re
import textwrap
from pathlib import Path

from fastapi.routing import APIRoute
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.api import main as modulo_main
from app.api import video as modulo_video
from app.bd import esquema
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "docs" / "tesis"
AVISO = ("<!-- Archivo generado por scripts/tesis/generar_docs.py: no se edita a mano. -->\n\n")
REQUISITO = re.compile(r"\b(?:RF|RNF|RN|HU|DT|D|A)-\d+\b")


# --- Esquema --------------------------------------------------------------------------------

def _comentarios_del_esquema() -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    """Comentario de cada tabla (líneas # justo antes) y de cada columna (# al final)."""
    lineas = Path(esquema.__file__).read_text(encoding="utf-8").splitlines()
    de_tabla, de_columna, tabla, previos = {}, {}, None, []
    for linea in lineas:
        limpia = linea.strip()
        if m := re.match(r"^(\w+) = Table\($", limpia):
            de_tabla[m.group(1)] = " ".join(previos)
            tabla = m.group(1)
        elif limpia.startswith("#"):
            previos.append(limpia.lstrip("# "))
            continue
        elif m := re.match(r'^Column\("(\w+)".*#\s*(.+)$', limpia):
            de_columna[(tabla, m.group(1))] = m.group(2)
        previos = []
    return de_tabla, de_columna


def _tipo(columna) -> str:
    """El tipo como lo crea PostgreSQL (p. ej. TIMESTAMP WITH TIME ZONE)."""
    return columna.type.compile(dialect=postgresql.dialect())


def _tablas():
    return [t for t in esquema.metadata.sorted_tables]


def generar_er() -> str:
    salida = [AVISO, "# Modelo entidad-relación\n\n",
              "Tablas de `app/bd/esquema.py` (PostgreSQL 18 en Neon; 17 en local y en el CI). "
              "PK = clave primaria, FK = clave foránea, UK = única.\n\n```mermaid\nerDiagram\n"]
    for t in _tablas():
        salida.append(f"  {t.name} {{\n")
        for c in t.columns:
            marcas = [m for m, si in (("PK", c.primary_key), ("FK", bool(c.foreign_keys)),
                                      ("UK", bool(c.unique))) if si]
            tipo = re.sub(r"\W+", "_", _tipo(c).split("(")[0]).lower()
            salida.append(f"    {tipo} {c.name}{' ' + ','.join(marcas) if marcas else ''}\n")
        salida.append("  }\n")
    for t in _tablas():
        for fk in sorted(t.foreign_keys, key=lambda f: f.parent.name):
            destino = fk.column.table.name
            unica = fk.parent.primary_key or fk.parent.unique
            salida.append(f'  {destino} ||--{"o|" if unica else "o{"} {t.name} : '
                          f'"{fk.parent.name}"\n')
    salida.append("```\n")
    return "".join(salida)


def _restricciones(t) -> list[str]:
    resultado = []
    for r in sorted(t.constraints, key=lambda x: str(x.name)):
        if isinstance(r, CheckConstraint):
            resultado.append(f"`{r.name}`: `{r.sqltext}`")
        elif isinstance(r, UniqueConstraint) and len(r.columns) > 1:
            resultado.append(f"`{r.name}`: única ({', '.join(c.name for c in r.columns)})")
    for i in sorted(t.indexes, key=lambda x: str(x.name)):
        if isinstance(i, Index):
            donde = i.dialect_options["postgresql"].get("where")
            resultado.append(f"`{i.name}`: {'índice único' if i.unique else 'índice'} "
                             f"({', '.join(c.name for c in i.columns)})"
                             + (f" donde `{donde}`" if donde is not None else ""))
    return resultado


def generar_diccionario() -> str:
    de_tabla, de_columna = _comentarios_del_esquema()
    salida = [AVISO, "# Diccionario de datos\n\n",
              f"{len(_tablas())} tablas, leídas de `app/bd/esquema.py` (la misma definición que "
              "usan las migraciones de Alembic). La descripción es el comentario del código; "
              "«—» quiere decir que el código no tiene comentario para esa columna.\n"]
    for t in _tablas():
        salida.append(f"\n## `{t.name}`\n\n")
        if de_tabla.get(t.name):
            salida.append(f"{de_tabla[t.name]}\n\n")
        salida.append("| Columna | Tipo | Nulo | Clave | Por defecto | Descripción |\n"
                      "|---|---|---|---|---|---|\n")
        for c in t.columns:
            clave = " ".join(filter(None, [
                "PK" if c.primary_key else "",
                "FK → " + ", ".join(f"{f.column.table.name}.{f.column.name}"
                                   for f in c.foreign_keys) if c.foreign_keys else "",
                "única" if c.unique else ""]))
            defecto = (str(c.server_default.arg) if c.server_default is not None
                       and hasattr(c.server_default, "arg") else "")
            defecto = getattr(c.server_default.arg, "text", defecto) if defecto else ""
            salida.append(f"| `{c.name}` | {_tipo(c)} | {'sí' if c.nullable else 'no'} | "
                          f"{clave or '—'} | {f'`{defecto}`' if defecto else '—'} | "
                          f"{de_columna.get((t.name, c.name), '—')} |\n")
        if restricciones := _restricciones(t):
            salida.append("\nRestricciones e índices: " + "; ".join(restricciones) + ".\n")
    return "".join(salida)


# --- Endpoints ------------------------------------------------------------------------------

def _app():
    return modulo_main.crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("R", capacidad=5)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("clave-falsa-solo-para-leer-las-rutas-0000"),
        token_video="token-falso-solo-para-leer-las-rutas",
        revisar_escalamientos_cada_s=None, procesar_avisos_cada_s=None,
        revisar_videos_cada_s=None)


def _funciones_locales(modulo) -> dict[str, ast.FunctionDef]:
    arbol = ast.parse(inspect.getsource(modulo))
    return {n.name: n for n in ast.walk(arbol)
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}


def _codigo(valor: ast.AST) -> set[int]:
    """201, status.HTTP_409_CONFLICT o «413 if ... else 415»."""
    if isinstance(valor, ast.IfExp):
        return _codigo(valor.body) | _codigo(valor.orelse)
    if isinstance(valor, ast.Constant) and isinstance(valor.value, int):
        return {valor.value}
    if isinstance(valor, ast.Attribute) and (m := re.search(r"_(\d{3})_", valor.attr)):
        return {int(m.group(1))}
    return set()


def _codigos_en(nodo: ast.AST, locales: dict, vistos: set[str]) -> set[int]:
    """Códigos de HTTPException(...) y status_code=... en la función y en las funciones
    locales que llama (un nivel por nombre, sin repetir)."""
    codigos = set()
    for n in ast.walk(nodo):
        if isinstance(n, ast.keyword) and n.arg == "status_code":
            codigos |= _codigo(n.value)
        if not isinstance(n, ast.Call):
            continue
        nombre = getattr(n.func, "id", getattr(n.func, "attr", ""))
        if nombre in ("HTTPException", "JSONResponse", "Response") and n.args:
            codigos |= _codigo(n.args[0])
        if nombre == "no_autenticado":  # app/api/seguridad.py: 401 con WWW-Authenticate
            codigos.add(401)
        if nombre in locales and nombre not in vistos:
            vistos.add(nombre)
            codigos |= _codigos_en(locales[nombre], locales, vistos)
    return codigos


def _roles(dependencia) -> tuple[set[str], bool]:
    roles, sesion = set(), False
    for d in dependencia.dependencies:
        nombre = getattr(d.call, "__name__", "")
        if nombre == "verificar" and d.call.__closure__:
            for celda in d.call.__closure__:
                if isinstance(celda.cell_contents, tuple):
                    roles |= {r.value for r in celda.cell_contents}
        if nombre in ("usuario_actual", "verificar"):
            sesion = True
        if nombre == "trabajador":
            roles.add("trabajador de video")
        r, s = _roles(d)
        roles, sesion = roles | r, sesion or s
    return roles, sesion


# Errores que lanzan los servicios del video y que la ruta traduce con _ejecutar
# (app/video/servicio.py, VideoRechazado(estado_http, ...)).
_DEL_SERVICIO_DE_VIDEO = {int(c) for c in re.findall(
    r"VideoRechazado\((\d{3})", Path(modulo_video.__file__).parent.parent.joinpath(
        "video", "servicio.py").read_text(encoding="utf-8"))}


def _rutas(rutas) -> list[APIRoute]:
    """Las rutas, también las de un router incluido (FastAPI reciente las envuelve)."""
    resultado = []
    for ruta in rutas:
        if isinstance(ruta, APIRoute):
            resultado.append(ruta)
        elif hasattr(ruta, "original_router"):
            resultado += _rutas(ruta.original_router.routes)
    return resultado


def generar_catalogo() -> str:
    app = _app()
    locales = {**_funciones_locales(modulo_main), **_funciones_locales(modulo_video)}
    filas = []
    for ruta in _rutas(app.routes):
        roles, sesion = _roles(ruta.dependant)
        funcion = ast.parse(textwrap.dedent(inspect.getsource(ruta.endpoint)))
        codigos = {ruta.status_code or 200} | _codigos_en(funcion, locales, set())
        if sesion or roles:
            codigos |= {401, 403} if roles - {"trabajador de video"} else {401}
        if "trabajador de video" in roles:
            codigos |= {401, 503}
        if "_ejecutar" in inspect.getsource(ruta.endpoint):
            codigos |= _DEL_SERVICIO_DE_VIDEO
        if ruta.dependant.body_params or ruta.dependant.query_params or ruta.dependant.path_params:
            codigos.add(422)
        texto = inspect.getsource(ruta.endpoint)
        requisitos = sorted(set(REQUISITO.findall(texto)), key=lambda r: (r.split("-")[0],
                                                                         int(r.split("-")[1])))
        quien = ", ".join(sorted(roles)) if roles else ("cualquier sesión" if sesion
                                                        else "público")
        for metodo in sorted(ruta.methods):
            filas.append(f"| {metodo} | `{ruta.path}` | {quien} | "
                         f"{', '.join(str(c) for c in sorted(codigos))} | "
                         f"{', '.join(requisitos) or '—'} |\n")
    return "".join([
        AVISO, "# Catálogo de endpoints\n\n",
        f"{len(filas)} rutas de la API, leídas de la app real (`crear_app`). **Quién** sale de "
        "`exigir_rol` (401 sin sesión, 403 con otro rol). **Códigos**: el de éxito, los que la "
        "ruta lanza con `HTTPException` (también en las funciones auxiliares que llama), 401/403 "
        "por la sesión, 422 si tiene parámetros o cuerpo que validar y, en el video, todos los "
        "que puede lanzar su servicio (`VideoRechazado`; no todos aplican a cada ruta). Además, "
        "cualquier petición con cuerpo de más de 1 MB recibe 413 "
        "(A-01). **Requisitos**: los que cita el código de la ruta.\n\n",
        "| Método | Ruta | Quién | Códigos | Requisitos |\n|---|---|---|---|---|\n", *filas])


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, contenido in (("er.md", generar_er()),
                              ("diccionario-datos.md", generar_diccionario()),
                              ("catalogo-endpoints.md", generar_catalogo())):
        (DESTINO / nombre).write_text(contenido, encoding="utf-8", newline="\n")
        print(f"docs/tesis/{nombre}")


if __name__ == "__main__":
    main()
