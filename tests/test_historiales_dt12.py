"""DT-12 (#265): los historiales no hacen una consulta por fila."""
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres
from tests.test_api import CLAVE, cliente


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioEnMemoria()


def reporte(codigo):
    return Reporte(codigo=codigo, descripcion="Perro herido en la calle, no se levanta",
                   ubicacion=Ubicacion(direccion="Calle 10"), estado=EstadoReporte.CLASIFICADO,
                   prioridad=Prioridad.ALTA, creado_en=datetime(2026, 11, 5, tzinfo=UTC))


def test_buscar_varios_trae_los_que_existen_en_una_consulta(repositorio):
    for codigo in ("AAAA0001", "BBBB0002"):
        repositorio.guardar(deepcopy(reporte(codigo)))
    encontrados = repositorio.buscar_varios(["AAAA0001", "BBBB0002", "NOEXISTE"])
    assert sorted(encontrados) == ["AAAA0001", "BBBB0002"]
    assert encontrados["AAAA0001"].prioridad == Prioridad.ALTA
    assert repositorio.buscar_varios([]) == {}


class ContarBusquedas(RepositorioEnMemoria):
    def __init__(self):
        super().__init__()
        self.busquedas = 0

    def buscar(self, codigo):
        self.busquedas += 1
        return super().buscar(codigo)


def test_el_historial_del_veterinario_no_busca_reporte_por_reporte():
    repo = ContarBusquedas()
    c = cliente(repo)
    vet = {"Authorization": "Bearer " + c.post("/auth/token", data={
        "username": "vet@patitas.co", "password": CLAVE}).json()["access_token"]}
    for n in range(3):
        texto = f"Perro atropellado que no se levanta {n}"
        codigo = c.post("/reportes", json={"descripcion": texto,
                                           "direccion": "Calle 10"}).json()["codigo"]
        assert c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=vet).status_code == 200
    repo.busquedas = 0
    filas = c.get("/veterinario/historial", headers=vet).json()
    assert len(filas) == 3 and all(f["estado"] == "confirmado" for f in filas)
    assert repo.busquedas == 0
