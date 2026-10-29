"""Administrador inicial creado por variables de entorno (fase 1, #67, RF-13).

Render (plan gratis) no da consola para ejecutar «crear_usuario»: la primera cuenta de
administración se crea sola al arrancar si PATITAS_ADMIN_CORREO y PATITAS_ADMIN_CONTRASENA
existen. Nunca reemplaza una cuenta que ya existe ni registra la contraseña en el log.
"""
import logging

import pytest
from sqlalchemy import text

from app.ajustes import cargar_ajustes_admin
from app.dominio.modelos import Rol
from app.usuarios.admin_inicial import crear_admin_inicial
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-del-admin"  # falsa, solo para pruebas


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for variable in ("PATITAS_ADMIN_CORREO", "PATITAS_ADMIN_CONTRASENA", "PATITAS_ADMIN_NOMBRE"):
        monkeypatch.delenv(variable, raising=False)


def ajustes(monkeypatch, **variables):
    for nombre, valor in variables.items():
        monkeypatch.setenv(nombre, valor)
    return cargar_ajustes_admin(archivo_env=None)


def test_crea_la_cuenta_de_administrador_si_no_existe(monkeypatch):
    repo = RepositorioUsuariosEnMemoria()
    a = ajustes(monkeypatch, PATITAS_ADMIN_CORREO=" Admin@Patitas.co ",
                PATITAS_ADMIN_CONTRASENA=CLAVE)
    assert crear_admin_inicial(repo, a) is True
    admin = repo.buscar_por_correo("admin@patitas.co")
    assert admin.rol == Rol.ADMINISTRADOR and admin.activo
    assert ServicioUsuarios(repo).autenticar("admin@patitas.co", CLAVE) is not None


def test_sin_variables_no_hace_nada(monkeypatch):
    repo = RepositorioUsuariosEnMemoria()
    assert crear_admin_inicial(repo, ajustes(monkeypatch)) is False
    assert crear_admin_inicial(repo, ajustes(monkeypatch, PATITAS_ADMIN_CORREO="")) is False


def test_no_reemplaza_una_cuenta_existente_ni_su_contrasena(monkeypatch):
    """Cada reinicio de Render vuelve a ejecutar el arranque: no debe pisar la cuenta."""
    repo = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(repo).registrar("admin@patitas.co", "Ana", Rol.VETERINARIO,
                                     "otra-clave-larga-de-prueba")
    a = ajustes(monkeypatch, PATITAS_ADMIN_CORREO="admin@patitas.co",
                PATITAS_ADMIN_CONTRASENA=CLAVE)
    assert crear_admin_inicial(repo, a) is False
    assert repo.buscar_por_correo("admin@patitas.co").rol == Rol.VETERINARIO


def test_contrasena_corta_no_crea_la_cuenta_ni_aparece_en_el_log(monkeypatch, caplog):
    repo = RepositorioUsuariosEnMemoria()
    a = ajustes(monkeypatch, PATITAS_ADMIN_CORREO="admin@patitas.co",
                PATITAS_ADMIN_CONTRASENA="corta123")
    with caplog.at_level(logging.WARNING):
        assert crear_admin_inicial(repo, a) is False
    assert repo.buscar_por_correo("admin@patitas.co") is None
    assert "corta123" not in caplog.text and "12" in caplog.text


def test_la_contrasena_no_aparece_al_imprimir_los_ajustes(monkeypatch):
    a = ajustes(monkeypatch, PATITAS_ADMIN_CORREO="admin@patitas.co",
                PATITAS_ADMIN_CONTRASENA=CLAVE)
    assert CLAVE not in repr(a) and CLAVE not in str(a)


@pytest.mark.postgres
def test_la_base_acepta_el_rol_administrador(bd_limpia):
    with bd_limpia.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO usuarios (correo, nombre, rol, hash_contrasena) "
            "VALUES ('admin@patitas.co', 'Admin', 'administrador', 'h')"))
