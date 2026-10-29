"""Copia la base de Render a Neon y comprueba que no falte nada (#154).

Lo ejecuta Brayan en su PC (necesita sus cuentas); el asistente no lo corre. Guía paso a paso:
docs/aprende/migrar-a-neon.md.

    python scripts/operacion/migrar_a_neon.py            # copia y verifica
    python scripts/operacion/migrar_a_neon.py --verificar # solo compara las dos bases

Pide las dos direcciones de conexión sin mostrarlas en pantalla. Las contraseñas nunca van en
la línea de comandos (otros programas del equipo podrían leerla): pg_dump y pg_restore las
reciben por la variable PGPASSWORD de su propio proceso. Al final imprime las variables que
hay que poner en Render, sin la contraseña.
"""
from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

CARPETAS_WINDOWS = [Path(rf"C:\Program Files\PostgreSQL\{v}\bin") for v in (18, 17, 16)]


@dataclass(frozen=True)
class Conexion:
    host: str
    puerto: int
    usuario: str
    contrasena: str
    base: str
    sslmode: str | None

    def entorno(self) -> dict[str, str]:
        """Variables de libpq para pg_dump, pg_restore y psycopg: nada en la línea de comandos."""
        variables = {"PGHOST": self.host, "PGPORT": str(self.puerto), "PGUSER": self.usuario,
                     "PGPASSWORD": self.contrasena, "PGDATABASE": self.base}
        if self.sslmode:
            variables["PGSSLMODE"] = self.sslmode
        return variables

    def variables_render(self) -> dict[str, str]:
        """Lo que va en Render → patitas-en-casa → Environment (sin la contraseña)."""
        variables = {"POSTGRES_HOST": self.host, "POSTGRES_PORT": str(self.puerto),
                     "POSTGRES_USER": self.usuario, "POSTGRES_DB": self.base}
        if self.sslmode:
            variables["POSTGRES_SSLMODE"] = self.sslmode
        return variables


def leer_url(url: str) -> Conexion:
    """postgresql://usuario:clave@host[:puerto]/base[?sslmode=require] → Conexion."""
    partes = urlsplit(url.strip())
    if partes.scheme not in ("postgres", "postgresql") or not partes.hostname:
        raise ValueError("La dirección debe empezar por postgresql:// y tener un servidor.")
    base = partes.path.lstrip("/")
    if not base or not partes.username or partes.password is None:
        raise ValueError("Falta el usuario, la contraseña o el nombre de la base.")
    sslmode = parse_qs(partes.query).get("sslmode", [None])[0]
    return Conexion(partes.hostname, partes.port or 5432, unquote(partes.username),
                    unquote(partes.password), base, sslmode)


def con_tls(conexion: Conexion) -> Conexion:
    """Render y Neon cifran las conexiones externas; «require» evita caer a texto plano."""
    return replace(conexion, sslmode=conexion.sslmode or "require")


def programa(nombre: str) -> str:
    """Ruta de pg_dump o pg_restore: el PATH o la instalación de PostgreSQL en Windows."""
    encontrado = shutil.which(nombre)
    if encontrado:
        return encontrado
    for carpeta in CARPETAS_WINDOWS:
        candidato = carpeta / f"{nombre}.exe"
        if candidato.exists():
            return str(candidato)
    raise SystemExit(f"No encuentro {nombre}. Instala PostgreSQL 17 (trae las herramientas).")


def ejecutar(comando: list[str], conexion: Conexion) -> None:
    resultado = subprocess.run(comando, env={**os.environ, **conexion.entorno()},
                               capture_output=True, text=True)
    if resultado.returncode != 0:
        # Los mensajes de pg_dump no incluyen la contraseña (va en PGPASSWORD).
        raise SystemExit(f"{Path(comando[0]).name} falló:\n{resultado.stderr.strip()}")


def contar_filas(conexion: Conexion) -> dict[str, int]:
    import psycopg  # de requirements.txt; aquí para que las pruebas no lo necesiten

    with psycopg.connect(**_kwargs(conexion)) as c:
        tablas = [f[0] for f in c.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")]
        return {t: c.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tablas}


def _kwargs(conexion: Conexion) -> dict[str, object]:
    datos = {"host": conexion.host, "port": conexion.puerto, "user": conexion.usuario,
             "password": conexion.contrasena, "dbname": conexion.base}
    if conexion.sslmode:
        datos["sslmode"] = conexion.sslmode
    return datos


def diferencias(origen: dict[str, int], destino: dict[str, int]) -> list[str]:
    """Tablas que faltan o no tienen las mismas filas; vacío = la copia está completa."""
    problemas = []
    for tabla in sorted(set(origen) | set(destino)):
        a, b = origen.get(tabla), destino.get(tabla)
        if a != b:
            problemas.append(f"{tabla}: Render {a if a is not None else 'no existe'}, "
                             f"Neon {b if b is not None else 'no existe'}")
    return problemas


def copiar(render: Conexion, neon: Conexion) -> None:
    with tempfile.TemporaryDirectory() as carpeta:
        copia = str(Path(carpeta) / "patitas.dump")
        print("1/3 Copiando la base de Render (pg_dump)…")
        ejecutar([programa("pg_dump"), "--format=custom", "--no-owner", "--no-acl",
                  "--file", copia], render)
        print("2/3 Cargándola en Neon (pg_restore)…")
        ejecutar([programa("pg_restore"), "--no-owner", "--no-acl", "--exit-on-error",
                  "--dbname", neon.base, copia], neon)
    # La carpeta temporal y la copia se borran aquí: los datos no quedan en el disco.


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--verificar", action="store_true",
                            help="no copia: solo compara las filas de las dos bases")
    opciones = argumentos.parse_args()
    print("Pega cada dirección y pulsa Enter (no se verá mientras la pegas).")
    render = leer_url(getpass.getpass("External Database URL de Render: "))
    neon = leer_url(getpass.getpass("Connection string de Neon: "))
    # Las dos solo aceptan conexiones cifradas desde fuera: se exige TLS siempre.
    render, neon = con_tls(render), con_tls(neon)
    if not opciones.verificar:
        if contar_filas(neon):
            raise SystemExit("La base de Neon ya tiene tablas. Usa una base vacía o --verificar.")
        copiar(render, neon)
    print("3/3 Comparando las filas de cada tabla…")
    problemas = diferencias(contar_filas(render), contar_filas(neon))
    if problemas:
        print("La copia NO está completa:\n- " + "\n- ".join(problemas))
        sys.exit(1)
    print("Copia completa: las mismas tablas y filas en las dos bases.\n")
    print("Pon esto en Render → patitas-en-casa → Environment (la contraseña la copias de Neon):")
    for nombre, valor in neon.variables_render().items():
        print(f"  {nombre}={valor}")
    print("  POSTGRES_PASSWORD=<la contraseña de Neon>")


if __name__ == "__main__":
    main()
