"""Auditoría A-03 (#239): la cola, las ofertas y el escalamiento no leen toda la historia."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres
from tests.test_api import CLAVE, cliente

BASE = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioEnMemoria()


def reporte(codigo, estado, prioridad=Prioridad.ALTA, horas=0):
    return Reporte(codigo=codigo, descripcion="Perro herido en la calle, no se levanta",
                   ubicacion=Ubicacion(direccion="Calle 10"), estado=estado,
                   prioridad=prioridad, creado_en=BASE + timedelta(hours=horas))


def cargar(repositorio):
    for r in (reporte("PEND0001", EstadoReporte.CLASIFICADO, horas=0),
              reporte("REVI0001", EstadoReporte.REQUIERE_REVISION, Prioridad.MEDIA, horas=1),
              reporte("CONF0001", EstadoReporte.CONFIRMADO, Prioridad.CRITICA, horas=-5),
              reporte("CONF0002", EstadoReporte.CONFIRMADO, Prioridad.BAJA, horas=-6),
              reporte("DESC0001", EstadoReporte.DESCARTADO, horas=-48)):
        repositorio.guardar(deepcopy(r))


def codigos(lista):
    return sorted(r.codigo for r in lista)


def test_pendientes_son_los_que_aun_no_decide_un_veterinario(repositorio):
    cargar(repositorio)
    assert codigos(repositorio.pendientes()) == ["PEND0001", "REVI0001"]


def test_creados_desde_incluye_el_limite(repositorio):
    cargar(repositorio)
    assert codigos(repositorio.creados_desde(BASE - timedelta(hours=5))) == [
        "CONF0001", "PEND0001", "REVI0001"]


def test_confirmados_de_rescate_son_criticos_o_altos(repositorio):
    cargar(repositorio)
    assert codigos(repositorio.confirmados_de_rescate()) == ["CONF0001"]


class SinTodos(RepositorioEnMemoria):
    def todos(self):
        raise AssertionError("no debe leer toda la historia de reportes")


def test_la_cola_y_las_ofertas_no_llaman_a_todos():
    c = cliente(SinTodos())
    c.post("/reportes", json={"descripcion": "Perro atropellado que no se puede levantar",
                              "direccion": "Calle 10 #5-20"})
    token = c.post("/auth/token", data={"username": "vet@patitas.co",
                                        "password": CLAVE}).json()["access_token"]
    r = c.get("/cola", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and len(r.json()) == 1


def test_ofertas_y_escalamiento_no_llaman_a_todos():
    from app.dominio.modelos import Rol, Usuario
    from app.rescates.repositorio import RepositorioRescatesEnMemoria
    from app.rescates.servicio import ServicioRescates
    repo = SinTodos()
    repo.guardar(reporte("CONF0001", EstadoReporte.CONFIRMADO, Prioridad.CRITICA))
    rescates = RepositorioRescatesEnMemoria()
    servicio = ServicioRescates(repo, rescates)
    rescatista = Usuario("r@patitas.co", "Rita", Rol.RESCATISTA, "hash")
    servicio.cambiar_disponibilidad(rescatista, True)
    assert [r.codigo for r in servicio.ofertas(rescatista)] == ["CONF0001"]
    assert servicio.escalar_vencidos() == []  # sin decisión registrada aún no vence
