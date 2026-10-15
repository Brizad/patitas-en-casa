"""Contrato de RepositorioCupos (DT-05): memoria y PostgreSQL cumplen lo mismo (RN-04)."""
import threading

import pytest
from sqlalchemy import text

from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Animal, Especie, Refugio
from tests.conftest import REFUGIO_DEMO, preparar_refugio


def animal(nombre="Luna"):
    return Animal(nombre=nombre, especie=Especie.PERRO, estado_salud="herida en pata",
                  vacunado=True)


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def fabrica(request):
    """Devuelve una función (capacidad, ocupados) -> repositorio de cupos."""
    if request.param == "postgres":
        motor = request.getfixturevalue("bd_limpia")

        def crear(capacidad, ocupados):
            preparar_refugio(motor, capacidad, ocupados)
            return RepositorioCuposPostgres.primer_refugio(motor)
        return crear
    return lambda capacidad, ocupados: RepositorioCuposEnMemoria(
        Refugio(REFUGIO_DEMO[0], capacidad, ocupados))


def test_refugio_refleja_el_estado_guardado(fabrica):
    refugio = fabrica(40, 12).refugio()
    assert (refugio.nombre, refugio.texto_ocupacion()) == (REFUGIO_DEMO[0], "12/40")


def test_ocupar_con_cupo_suma_uno_y_devuelve_el_refugio(fabrica):
    repositorio = fabrica(40, 35)
    assert repositorio.ocupar_cupo(animal()).texto_ocupacion() == "36/40"
    assert repositorio.refugio().texto_ocupacion() == "36/40"


def test_sin_cupo_devuelve_none_y_no_cambia_nada(fabrica):
    repositorio = fabrica(2, 2)
    assert repositorio.ocupar_cupo(animal()) is None
    assert repositorio.refugio().texto_ocupacion() == "2/2"


def test_ingresos_simultaneos_nunca_superan_la_capacidad(fabrica):
    """CA-20 / BUG-04: 10 ingresos a la vez con 5 cupos libres => entran exactamente 5."""
    repositorio = fabrica(40, 35)
    salida = threading.Barrier(10)
    aceptados = []

    def ingresar(i):
        salida.wait()  # todos los hilos arrancan al mismo tiempo
        if repositorio.ocupar_cupo(animal(f"Animal {i}")) is not None:
            aceptados.append(i)

    hilos = [threading.Thread(target=ingresar, args=(i,)) for i in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert len(aceptados) == 5
    assert repositorio.refugio().texto_ocupacion() == "40/40"


@pytest.mark.postgres
def test_postgres_guarda_la_ficha_del_animal(bd_limpia):
    repositorio = RepositorioCuposPostgres.primer_refugio(bd_limpia)
    repositorio.ocupar_cupo(animal("Canela"))
    with bd_limpia.connect() as conexion:
        fila = conexion.execute(text(
            "SELECT nombre, especie, estado_salud, vacunado, esterilizado, refugio_id "
            "FROM animales")).one()
    assert tuple(fila) == ("Canela", "perro", "herida en pata", True, False, 1)


@pytest.mark.postgres
def test_postgres_sin_refugios_da_un_error_claro(bd_limpia):
    with bd_limpia.begin() as conexion:
        conexion.execute(text("TRUNCATE TABLE refugios CASCADE"))
    with pytest.raises(LookupError, match="refugio"):
        RepositorioCuposPostgres.primer_refugio(bd_limpia)
