"""Rendimiento de `/indicadores`: antes hacía una consulta por reporte, otra por decisión y
otra por solicitud (N+1). Ahora el número de consultas es fijo y el resultado es el mismo."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.adopciones.modelos import (
    Energia,
    EstadoSolicitud,
    Publicacion,
    Seguimiento,
    Solicitud,
    Tamano,
)
from app.adopciones.repositorio import RepositorioAdopcionesEnMemoria
from app.adopciones.repositorio_postgres import RepositorioAdopcionesPostgres
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Animal, Especie, EstadoReporte, Prioridad, Refugio, Reporte, Rol
from app.dominio.modelos import Ubicacion as Lugar
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.rescates.repositorio import RepositorioRescatesEnMemoria
from app.rescates.repositorio_postgres import RepositorioRescatesPostgres
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios
from tests.test_decision_adopcion import CLAVE, en_postgres, h, preparar
from tests.test_repositorio_contrato import decision

MOMENTO = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)
CODIGOS = ("AAAA0001", "BBBB0002", "CCCC0003")


def _reporte(codigo: str) -> Reporte:
    return Reporte(codigo=codigo, descripcion="Perro atropellado que no se puede levantar",
                   ubicacion=Lugar(direccion="Calle 10"), estado=EstadoReporte.CLASIFICADO,
                   prioridad=Prioridad.CRITICA, creado_en=MOMENTO)


# --- Contratos de los tres métodos nuevos: memoria y PostgreSQL responden lo mismo ---

@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorios(request):
    """(reportes, rescates) con tres reportes guardados."""
    if request.param == "postgres":
        motor = request.getfixturevalue("bd_limpia")
        reportes, rescates = RepositorioPostgres(motor), RepositorioRescatesPostgres(motor)
    else:
        reportes, rescates = RepositorioEnMemoria(), RepositorioRescatesEnMemoria()
    for codigo in CODIGOS:
        reportes.guardar(_reporte(codigo))
    return reportes, rescates


def test_ultimas_decisiones_trae_solo_los_reportes_decididos(repositorios):
    reportes, _ = repositorios
    assert reportes.ultimas_decisiones() == {}
    reportes.confirmar(decision(codigo="AAAA0001"))
    reportes.confirmar(decision(codigo="CCCC0003", final=Prioridad.CRITICA))
    ultimas = reportes.ultimas_decisiones()
    assert sorted(ultimas) == ["AAAA0001", "CCCC0003"]
    assert ultimas["AAAA0001"] == reportes.decisiones("AAAA0001")[-1]
    assert ultimas["CCCC0003"].prioridad_final == Prioridad.CRITICA


def test_vigentes_trae_los_rescates_en_curso_de_una_vez(repositorios):
    _, rescates = repositorios
    assert rescates.vigentes() == []
    rescates.aceptar("AAAA0001", "ana@rescate.co", MOMENTO)
    rescates.aceptar("BBBB0002", "luis@rescate.co", MOMENTO)
    vigentes = sorted(rescates.vigentes(), key=lambda r: r.codigo)
    assert vigentes == [rescates.vigente("AAAA0001"), rescates.vigente("BBBB0002")]


def _con_seguimientos(repo, animal_id: int) -> int:
    solicitud = Solicitud(None, animal_id, "lau@correo.co", "", EstadoSolicitud.PENDIENTE,
                          MOMENTO)
    assert repo.crear_solicitud(solicitud)
    plan = [Seguimiento(None, solicitud.id, dia, MOMENTO + timedelta(days=dia))
            for dia in (30, 90, 180)]
    assert repo.aprobar(solicitud.id, "coord@patitas.co", MOMENTO, plan)
    return solicitud.id


def _contrato_de_seguimientos(repo, animal_id: int) -> None:
    assert repo.todos_los_seguimientos() == []
    solicitud_id = _con_seguimientos(repo, animal_id)
    todos = repo.todos_los_seguimientos()
    assert todos == repo.seguimientos(solicitud_id)
    assert [x.dia for x in todos] == [30, 90, 180]


PUBLICACION = ("Perrita juguetona que ama correr", Tamano.MEDIANO, Energia.ALTA, 12, True,
               True, True)


def test_todos_los_seguimientos_en_memoria():
    repo = RepositorioAdopcionesEnMemoria()
    repo.publicar(Publicacion(1, *PUBLICACION))
    _contrato_de_seguimientos(repo, 1)


@pytest.mark.postgres
def test_todos_los_seguimientos_en_postgres(bd_limpia):
    usuarios = ServicioUsuarios(RepositorioUsuariosPostgres(bd_limpia))
    usuarios.registrar("lau@correo.co", "Laura", Rol.ADOPTANTE, CLAVE)
    usuarios.registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    luna = Animal("Luna", Especie.PERRO, "sana")
    RepositorioCuposPostgres.primer_refugio(bd_limpia).ocupar_cupo(luna)
    repo = RepositorioAdopcionesPostgres(bd_limpia)
    repo.publicar(Publicacion(luna.id, *PUBLICACION))
    _contrato_de_seguimientos(repo, luna.id)


# --- La ruta: ya no pregunta de a uno ---

class _Llamadas:
    total = 0


def _contando(clase, metodo: str):
    """Una subclase del repositorio que cuenta las llamadas «de a uno» que hacía el N+1."""
    def contar(self, *argumentos):
        _Llamadas.total += 1
        return getattr(clase, metodo)(self, *argumentos)
    return type(f"{clase.__name__}Contado", (clase,), {metodo: contar})


def _app_que_cuenta() -> TestClient:
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    cupos = RepositorioCuposEnMemoria(Refugio("Demo", 40))
    return TestClient(crear_app(
        _contando(RepositorioEnMemoria, "decisiones")(), cupos, repositorio_usuarios=usuarios,
        repositorio_rescates=_contando(RepositorioRescatesEnMemoria, "vigente")(),
        repositorio_adopciones=_contando(RepositorioAdopcionesEnMemoria, "seguimientos")(cupos),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def test_los_indicadores_no_preguntan_reporte_por_reporte_ni_solicitud_por_solicitud():
    c = _app_que_cuenta()
    coordinador, _, ids = preparar(c)
    c.post(f"/refugio/solicitudes/{ids['lau@correo.co']}/decision", json={"aprobar": True},
           headers=coordinador)
    for n in range(6):
        c.post("/reportes", json={"descripcion": f"Perro atropellado que no se levanta {n}",
                                  "direccion": "Calle 10"})
    _Llamadas.total = 0
    cuerpo = c.get("/indicadores", headers=coordinador).json()
    assert _Llamadas.total == 0
    assert cuerpo["reportes"]["total"] == 6  # y el resultado sigue completo


@pytest.mark.postgres
def test_en_postgres_las_consultas_no_crecen_con_el_numero_de_reportes(bd_limpia):
    """Lo que importa en Render: cada consulta es un viaje de ida y vuelta a Neon."""
    c = en_postgres(bd_limpia)
    coordinador = h(c, "coord@patitas.co")

    def consultas() -> int:
        cuenta = {"n": 0}

        def contar(*_):
            cuenta["n"] += 1
        event.listen(bd_limpia, "before_cursor_execute", contar)
        try:
            assert c.get("/indicadores", headers=coordinador).status_code == 200
        finally:
            event.remove(bd_limpia, "before_cursor_execute", contar)
        return cuenta["n"]

    c.post("/reportes", json={"descripcion": "Perro atropellado que no se levanta ya",
                              "direccion": "Calle 10"})
    con_uno = consultas()
    for n in range(8):
        c.post("/reportes", json={"descripcion": f"Perro atropellado que no se levanta {n}",
                                  "direccion": "Calle 10"})
    assert consultas() == con_uno
