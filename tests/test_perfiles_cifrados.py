"""RNF-08 (#149): el perfil del adoptante queda ilegible en la base sin la clave."""
import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import select

from app.adopciones.modelos import PerfilAdoptante, Vivienda
from app.adopciones.repositorio_postgres import RepositorioAdopcionesPostgres
from app.bd.esquema import perfiles_adoptante
from app.dominio.modelos import Rol
from app.seguridad.cifrado import Cifrador
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios

pytestmark = pytest.mark.postgres

CIFRADOR = Cifrador("clave-de-datos-falsa-con-mas-de-32-caracteres")
PERFIL = PerfilAdoptante("lau@correo.co", Vivienda.APARTAMENTO, False, True, False, 7, True,
                         True)


@pytest.fixture
def motor(bd_limpia):
    ServicioUsuarios(RepositorioUsuariosPostgres(bd_limpia)).registrar(
        "lau@correo.co", "Laura", Rol.ADOPTANTE, "clave-de-prueba-larga")
    return bd_limpia


def fila(motor):
    with motor.connect() as c:
        return c.execute(select(perfiles_adoptante)).mappings().one()


def test_con_la_clave_la_fila_no_tiene_nada_en_claro(motor):
    RepositorioAdopcionesPostgres(motor, CIFRADOR).guardar_perfil(PERFIL)
    f = fila(motor)
    assert f["vivienda"] is None and f["hay_ninos"] is None and f["horas_solo_al_dia"] is None
    assert "apartamento" not in f["datos_cifrados"]
    leido = RepositorioAdopcionesPostgres(motor, CIFRADOR).perfil("lau@correo.co")
    assert (leido.vivienda, leido.hay_ninos, leido.horas_solo_al_dia) == (
        Vivienda.APARTAMENTO, True, 7)


def test_los_perfiles_en_claro_se_cifran_una_sola_vez(motor):
    RepositorioAdopcionesPostgres(motor).guardar_perfil(PERFIL)  # antes de la 0026
    assert fila(motor)["vivienda"] == "apartamento"
    repo = RepositorioAdopcionesPostgres(motor, CIFRADOR)
    assert repo.cifrar_perfiles_en_claro() == 1
    assert fila(motor)["vivienda"] is None
    assert repo.cifrar_perfiles_en_claro() == 0
    assert repo.perfiles()[0].horas_solo_al_dia == 7


def test_sin_la_clave_no_se_puede_leer_un_perfil_cifrado(motor):
    RepositorioAdopcionesPostgres(motor, CIFRADOR).guardar_perfil(PERFIL)
    with pytest.raises(RuntimeError, match="PATITAS_CLAVE_DATOS"):
        RepositorioAdopcionesPostgres(motor).perfil("lau@correo.co")


def test_con_otra_clave_tampoco(motor):
    RepositorioAdopcionesPostgres(motor, CIFRADOR).guardar_perfil(PERFIL)
    otra = Cifrador("otra-clave-de-datos-falsa-con-mas-de-32-caracteres")
    with pytest.raises(InvalidTag):  # GCM detecta la clave equivocada
        RepositorioAdopcionesPostgres(motor, otra).perfil("lau@correo.co")
