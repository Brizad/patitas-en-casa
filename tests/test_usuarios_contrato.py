"""Contrato de RepositorioUsuarios: memoria y PostgreSQL (DT-02, parte 1)."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.dominio.modelos import Rol, Usuario
from app.usuarios.repositorio import CorreoDuplicado, RepositorioUsuariosEnMemoria
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres

HASH_FALSO = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdGZhbHNh$aGFzaGZhbHNv"


def usuario(correo="vet@patitas.co", rol=Rol.VETERINARIO):
    return Usuario(correo=correo, nombre="Ana Vet", rol=rol, hash_contrasena=HASH_FALSO)


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioUsuariosPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioUsuariosEnMemoria()


def test_crear_y_buscar_conserva_los_campos(repositorio):
    repositorio.crear(usuario())
    encontrado = repositorio.buscar_por_correo("vet@patitas.co")
    assert encontrado == usuario()


def test_buscar_correo_inexistente_devuelve_none(repositorio):
    assert repositorio.buscar_por_correo("nadie@patitas.co") is None


def test_correo_repetido_lanza_correo_duplicado(repositorio):
    repositorio.crear(usuario())
    with pytest.raises(CorreoDuplicado):
        repositorio.crear(usuario(rol=Rol.COORDINADOR))


def test_actualizar_hash(repositorio):
    repositorio.crear(usuario())
    repositorio.actualizar_hash("vet@patitas.co", "$argon2id$nuevo")
    assert repositorio.buscar_por_correo("vet@patitas.co").hash_contrasena == "$argon2id$nuevo"


@pytest.mark.postgres
@pytest.mark.parametrize("columna, valor", [("rol", "ciudadano"), ("correo", "Vet@Patitas.co")])
def test_la_base_rechaza_roles_desconocidos_y_correos_con_mayusculas(bd_limpia, columna, valor):
    fila = {"correo": "vet@patitas.co", "rol": "veterinario", columna: valor}
    with pytest.raises(IntegrityError), bd_limpia.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO usuarios (correo, nombre, rol, hash_contrasena) "
            "VALUES (:correo, 'Ana', :rol, 'h')"), fila)
