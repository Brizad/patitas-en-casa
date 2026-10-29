"""D-06 (fechas de la API en UTC) y D-07 (justificación sin relleno), fase 2 (#75).

D-06: la bitácora devolvía la hora con -05:00 (zona de la sesión de PostgreSQL) y el
seguimiento con +00:00: el mismo instante con dos formatos. Ahora toda fecha de la API sale
en UTC.
D-07: «..........» cumplía RN-16 porque solo se contaban caracteres. Ahora la justificación
también exige letras (mínimo config.MIN_LETRAS_JUSTIFICACION).
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import (
    DecisionTriaje,
    EstadoReporte,
    Prioridad,
    Refugio,
    Reporte,
    Rol,
    Ubicacion,
    Usuario,
)
from app.reportes.confirmacion import AjusteSinJustificacion, ServicioConfirmacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
VET = Usuario("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, hash_contrasena="x")
BOGOTA = timezone(timedelta(hours=-5))


def reporte(codigo="ABCD1234"):
    return Reporte(codigo=codigo, descripcion="Perro con una herida en la pata trasera",
                   ubicacion=Ubicacion(direccion="Calle 10"), prioridad=Prioridad.MEDIA,
                   confianza=0.7, estado=EstadoReporte.CLASIFICADO,
                   creado_en=datetime(2026, 10, 28, 7, 0, tzinfo=BOGOTA))


@pytest.mark.parametrize("relleno", ["..........", "1234567890", "- - - - - -", "aa........"])
def test_d07_justificacion_de_relleno_se_rechaza(relleno):
    repositorio = RepositorioEnMemoria()
    repositorio.guardar(reporte())
    with pytest.raises(AjusteSinJustificacion, match="letras"):
        ServicioConfirmacion(repositorio).confirmar("ABCD1234", VET, Prioridad.ALTA, relleno)
    assert repositorio.buscar("ABCD1234").estado == EstadoReporte.CLASIFICADO


def test_d07_una_justificacion_real_corta_sigue_valiendo():
    repositorio = RepositorioEnMemoria()
    repositorio.guardar(reporte())
    decision = ServicioConfirmacion(repositorio).confirmar(
        "ABCD1234", VET, Prioridad.ALTA, "Sangra mucho")
    assert decision.justificacion == "Sangra mucho"


def test_d06_bitacora_seguimiento_y_ofertas_salen_en_utc():
    repositorio = RepositorioEnMemoria()
    repositorio.guardar(reporte())
    repositorio.confirmar(DecisionTriaje(
        "ABCD1234", "vet@patitas.co", Prioridad.MEDIA, Prioridad.MEDIA,
        decidido_en=datetime(2026, 10, 28, 8, 30, tzinfo=BOGOTA)))
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    c = TestClient(crear_app(repositorio, RepositorioCuposEnMemoria(Refugio("Demo", 40)),
                             repositorio_usuarios=usuarios,
                             emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-c")))
    token = c.post("/auth/token", data={"username": "vet@patitas.co", "password": CLAVE})
    h = {"Authorization": f"Bearer {token.json()['access_token']}"}
    (decision,) = c.get("/reportes/ABCD1234/decisiones", headers=h).json()
    assert decision["decidido_en"] == "2026-10-28T13:30:00+00:00"
    seguimiento = c.get("/reportes/ABCD1234/seguimiento").json()
    assert seguimiento["ultimo_cambio"].endswith("+00:00")
    assert all(p["fecha"] is None or p["fecha"].endswith("+00:00")
               for p in seguimiento["pasos"])
