"""Historial del veterinario: lo que él confirmó, ajustó o descartó, del más reciente al más viejo.

Sale de la bitácora `decisiones_triaje` (confirmar y ajustar) y de `descartes`. El repositorio
responde por veterinario (memoria y PostgreSQL) y la API lo expone solo a ese rol.
"""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import (
    DecisionTriaje,
    Descarte,
    EstadoReporte,
    MotivoDescarte,
    Prioridad,
    Refugio,
    Reporte,
    Rol,
    Ubicacion,
)
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
ANA, BEA = "ana@patitas.co", "bea@patitas.co"
JUSTIFICACION = "Tiene una fractura expuesta visible en la foto"


def reporte(codigo):
    return Reporte(codigo=codigo, descripcion="Perro herido en la esquina del parque",
                   ubicacion=Ubicacion(7.89, -72.5), prioridad=Prioridad.ALTA,
                   confianza=0.7, estado=EstadoReporte.CLASIFICADO)


def momento(dia):
    return datetime(2026, 10, dia, 14, 0, tzinfo=UTC)


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    repo = (RepositorioPostgres(request.getfixturevalue("bd_limpia"))
            if request.param == "postgres" else RepositorioEnMemoria())
    for codigo in ("AAAA1111", "BBBB2222", "CCCC3333", "DDDD4444"):
        repo.guardar(reporte(codigo))
    return repo


def test_el_repositorio_separa_las_decisiones_por_veterinario(repositorio):
    repositorio.confirmar(DecisionTriaje("AAAA1111", ANA, Prioridad.ALTA, Prioridad.ALTA,
                                         decidido_en=momento(1)))
    repositorio.confirmar(DecisionTriaje("BBBB2222", BEA, Prioridad.ALTA, Prioridad.CRITICA,
                                         JUSTIFICACION, decidido_en=momento(2)))
    repositorio.descartar(Descarte("CCCC3333", ANA, MotivoDescarte.FALSO, JUSTIFICACION,
                                   descartado_en=momento(3)))
    assert [d.codigo for d in repositorio.decisiones_de(ANA)] == ["AAAA1111"]
    assert [d.codigo for d in repositorio.decisiones_de(BEA)] == ["BBBB2222"]
    assert [d.codigo for d in repositorio.descartes_de(ANA)] == ["CCCC3333"]
    assert repositorio.descartes_de(BEA) == []
    assert repositorio.decisiones_de("nadie@patitas.co") == []


# --- API ---------------------------------------------------------------------

def cliente():
    usuarios = RepositorioUsuariosEnMemoria()
    for correo, rol in ((ANA, Rol.VETERINARIO), (BEA, Rol.VETERINARIO),
                        ("coord@patitas.co", Rol.COORDINADOR),
                        ("res@patitas.co", Rol.RESCATISTA)):
        ServicioUsuarios(usuarios).registrar(correo, correo, rol, CLAVE)
    repo = RepositorioEnMemoria()
    for codigo in ("AAAA1111", "BBBB2222", "CCCC3333", "DDDD4444"):
        repo.guardar(reporte(codigo))
    c = TestClient(crear_app(
        repo, RepositorioCuposEnMemoria(Refugio("Demo", 40)), repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))
    return c, repo


def sesion(c, correo=ANA):
    t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_historial_sin_sesion_da_401():
    c, _ = cliente()
    assert c.get("/veterinario/historial").status_code == 401


@pytest.mark.parametrize("correo", ["coord@patitas.co", "res@patitas.co"])
def test_historial_de_otro_rol_da_403(correo):
    c, _ = cliente()
    assert c.get("/veterinario/historial", headers=sesion(c, correo)).status_code == 403


def test_historial_muestra_solo_lo_mio_del_mas_reciente_al_mas_viejo():
    c, repo = cliente()
    repo.confirmar(DecisionTriaje("AAAA1111", ANA, Prioridad.ALTA, Prioridad.ALTA,
                                  decidido_en=momento(1)))
    repo.confirmar(DecisionTriaje("BBBB2222", ANA, Prioridad.ALTA, Prioridad.CRITICA,
                                  JUSTIFICACION, decidido_en=momento(3)))
    repo.descartar(Descarte("CCCC3333", ANA, MotivoDescarte.DUPLICADO, JUSTIFICACION,
                            duplicado_de="AAAA1111", descartado_en=momento(2)))
    repo.confirmar(DecisionTriaje("DDDD4444", BEA, Prioridad.ALTA, Prioridad.ALTA,
                                  decidido_en=momento(4)))
    historial = c.get("/veterinario/historial", headers=sesion(c)).json()
    assert [h["codigo"] for h in historial] == ["BBBB2222", "CCCC3333", "AAAA1111"]
    ajustado, descartado, confirmado = historial
    assert (ajustado["accion"], ajustado["prioridad_sugerida"], ajustado["prioridad_final"],
            ajustado["justificacion"], ajustado["estado"]) == (
        "ajustado", "alta", "critica", JUSTIFICACION, "confirmado")
    assert ajustado["fecha"] == "2026-10-03T14:00:00+00:00"
    assert (confirmado["accion"], confirmado["justificacion"]) == ("confirmado", None)
    assert (descartado["accion"], descartado["prioridad_final"], descartado["estado"]) == (
        "descartado", None, "descartado")
    assert descartado["justificacion"] == JUSTIFICACION


def test_historial_vacio_si_no_decidio_nada():
    c, _ = cliente()
    assert c.get("/veterinario/historial", headers=sesion(c, BEA)).json() == []
