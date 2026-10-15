"""Cuentas de personal y contraseñas Argon2id (DT-02, parte 1; RNF-05)."""
import pytest
from argon2 import PasswordHasher

from app.dominio.modelos import Rol, Usuario
from app.usuarios.contrasenas import ContrasenaInvalida, hashear, verificar
from app.usuarios.crear_usuario import main as crear_usuario
from app.usuarios.repositorio import CorreoDuplicado, RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # contraseña falsa, solo para pruebas


def servicio():
    return ServicioUsuarios(RepositorioUsuariosEnMemoria())


def test_el_hash_es_argon2id_y_no_contiene_la_contrasena():
    h = hashear(CLAVE)
    assert h.startswith("$argon2id$")
    assert CLAVE not in h


def test_la_misma_contrasena_da_hashes_distintos():
    """Cada hash lleva su propia sal aleatoria."""
    assert hashear(CLAVE) != hashear(CLAVE)


def test_verificar_acepta_la_correcta_y_rechaza_las_demas():
    h = hashear(CLAVE)
    assert verificar(h, CLAVE)
    assert not verificar(h, "otra-clave-cualquiera")
    assert not verificar("no-es-un-hash", CLAVE)


def test_registrar_y_autenticar():
    s = servicio()
    s.registrar("Vet@Patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    usuario = s.autenticar("vet@patitas.co", CLAVE)
    assert usuario is not None
    assert (usuario.correo, usuario.rol) == ("vet@patitas.co", Rol.VETERINARIO)


def test_contrasena_incorrecta_o_correo_desconocido_no_autentican():
    s = servicio()
    s.registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    assert s.autenticar("vet@patitas.co", "clave-equivocada-123") is None
    assert s.autenticar("nadie@patitas.co", CLAVE) is None


def test_usuario_inactivo_no_autentica():
    repositorio = RepositorioUsuariosEnMemoria()
    s = ServicioUsuarios(repositorio)
    s.registrar("coord@patitas.co", "Coordinación", Rol.COORDINADOR, CLAVE)
    repositorio.buscar_por_correo("coord@patitas.co").activo = False
    assert s.autenticar("coord@patitas.co", CLAVE) is None


@pytest.mark.parametrize("contrasena", ["corta", "a" * 11, "a" * 129])
def test_politica_de_contrasenas(contrasena):
    with pytest.raises(ContrasenaInvalida):
        servicio().registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, contrasena)


@pytest.mark.parametrize("correo", ["", "sin-arroba", "a@b", "con espacio@patitas.co"])
def test_correo_invalido_se_rechaza(correo):
    with pytest.raises(ValueError, match="correo"):
        servicio().registrar(correo, "Ana Vet", Rol.VETERINARIO, CLAVE)


def test_correo_repetido_se_rechaza_sin_importar_mayusculas():
    s = servicio()
    s.registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    with pytest.raises(CorreoDuplicado):
        s.registrar("VET@patitas.co", "Otra", Rol.COORDINADOR, CLAVE)


def test_hash_con_parametros_debiles_se_actualiza_al_iniciar_sesion():
    """Si mañana se suben los parámetros de Argon2id, los hashes viejos se renuevan solos."""
    repositorio = RepositorioUsuariosEnMemoria()
    debil = PasswordHasher(time_cost=1, memory_cost=8192).hash(CLAVE)
    repositorio.crear(Usuario("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, debil))
    assert ServicioUsuarios(repositorio).autenticar("vet@patitas.co", CLAVE) is not None
    nuevo = repositorio.buscar_por_correo("vet@patitas.co").hash_contrasena
    assert nuevo != debil and verificar(nuevo, CLAVE)


def test_nombre_vacio_se_rechaza():
    with pytest.raises(ValueError, match="nombre"):
        servicio().registrar("vet@patitas.co", "   ", Rol.VETERINARIO, CLAVE)


def test_comando_crear_usuario_explica_por_que_no_creo_la_cuenta():
    salida = []
    codigo = crear_usuario(
        ["--correo", "coord@patitas.co", "--nombre", "Coordinación", "--rol", "coordinador"],
        repositorio=RepositorioUsuariosEnMemoria(), pedir_contrasena=lambda _: "corta",
        mostrar=salida.append)
    assert codigo == 1
    assert "12" in salida[0]


def test_el_hash_no_aparece_al_imprimir_el_usuario():
    usuario = servicio().registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    assert "argon2" not in repr(usuario)


def test_comando_crear_usuario_pide_la_contrasena_dos_veces():
    repositorio = RepositorioUsuariosEnMemoria()
    respuestas = iter([CLAVE, CLAVE])
    salida = []
    codigo = crear_usuario(
        ["--correo", "coord@patitas.co", "--nombre", "Coordinación", "--rol", "coordinador"],
        repositorio=repositorio, pedir_contrasena=lambda _: next(respuestas),
        mostrar=salida.append)
    assert codigo == 0
    assert repositorio.buscar_por_correo("coord@patitas.co").rol == Rol.COORDINADOR
    assert CLAVE not in " ".join(salida)


def test_comando_crear_usuario_rechaza_confirmacion_distinta():
    repositorio = RepositorioUsuariosEnMemoria()
    respuestas = iter([CLAVE, CLAVE + "x"])
    codigo = crear_usuario(
        ["--correo", "coord@patitas.co", "--nombre", "Coordinación", "--rol", "coordinador"],
        repositorio=repositorio, pedir_contrasena=lambda _: next(respuestas),
        mostrar=lambda _: None)
    assert codigo == 1
    assert repositorio.buscar_por_correo("coord@patitas.co") is None
