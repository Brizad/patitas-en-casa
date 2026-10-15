"""Crea una cuenta de personal en la base de datos del .env (DT-02).

Uso:
    python -m app.usuarios.crear_usuario --correo ana@refugio.co --nombre "Ana" --rol veterinario

La contraseña se pide por teclado sin mostrarla y nunca se escribe en archivos ni en la consola.
"""
from __future__ import annotations

import argparse
import getpass
from collections.abc import Callable, Sequence

from app.dominio.modelos import Rol
from app.usuarios.contrasenas import ContrasenaInvalida
from app.usuarios.repositorio import CorreoDuplicado, RepositorioUsuarios
from app.usuarios.servicio import ServicioUsuarios


def _repositorio_desde_entorno() -> RepositorioUsuarios:
    from app.api.main import motor_desde_entorno
    from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres

    return RepositorioUsuariosPostgres(motor_desde_entorno())


def main(argv: Sequence[str] | None = None, repositorio: RepositorioUsuarios | None = None,
         pedir_contrasena: Callable[[str], str] = getpass.getpass,
         mostrar: Callable[[str], None] = print) -> int:
    parser = argparse.ArgumentParser(description="Crear una cuenta de personal.")
    parser.add_argument("--correo", required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--rol", required=True, choices=[r.value for r in Rol])
    args = parser.parse_args(argv)

    contrasena = pedir_contrasena("Contraseña (mínimo 12 caracteres): ")
    if pedir_contrasena("Repite la contraseña: ") != contrasena:
        mostrar("Las contraseñas no coinciden. No se creó la cuenta.")
        return 1
    servicio = ServicioUsuarios(repositorio or _repositorio_desde_entorno())
    try:
        usuario = servicio.registrar(args.correo, args.nombre, Rol(args.rol), contrasena)
    except (ContrasenaInvalida, CorreoDuplicado, ValueError) as error:
        mostrar(f"No se creó la cuenta: {error}")
        return 1
    mostrar(f"Cuenta creada: {usuario.correo} ({usuario.rol.value}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
