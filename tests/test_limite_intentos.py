"""Límite de intentos fallidos de inicio de sesión por correo y por IP (DT-06)."""
import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.intentos import LimiteIntentos, RepositorioIntentosEnMemoria
from app.usuarios.intentos_postgres import RepositorioIntentosPostgres
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

# Valores falsos, solo para pruebas.
SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"
CLAVE = "clave-de-prueba-larga"
CLAVE_MALA = "clave-equivocada-123"
INICIO = datetime(2026, 10, 15, 8, 0, tzinfo=UTC)
ANTES = INICIO - timedelta(minutes=1)


class Reloj:
    """Reloj que la prueba adelanta a mano."""

    def __init__(self) -> None:
        self.ahora = INICIO

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **tiempo) -> None:
        self.ahora += timedelta(**tiempo)


# --- Contrato del repositorio ----------------------------------------------

@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioIntentosPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioIntentosEnMemoria()


def test_fallos_desde_devuelve_solo_los_recientes_en_orden(repositorio):
    for minutos in (20, 0, 5):
        repositorio.registrar_fallo("correo:vet@patitas.co", INICIO + timedelta(minutes=minutos))
    assert repositorio.fallos_desde("correo:vet@patitas.co", INICIO + timedelta(minutes=1)) == [
        INICIO + timedelta(minutes=5), INICIO + timedelta(minutes=20)]


def test_las_claves_no_se_mezclan(repositorio):
    repositorio.registrar_fallo("correo:vet@patitas.co", INICIO)
    repositorio.registrar_fallo("ip:10.0.0.1", INICIO)
    assert repositorio.fallos_desde("correo:otra@patitas.co", ANTES) == []
    assert len(repositorio.fallos_desde("ip:10.0.0.1", ANTES)) == 1


def test_limpiar_borra_solo_esa_clave(repositorio):
    repositorio.registrar_fallo("correo:vet@patitas.co", INICIO)
    repositorio.registrar_fallo("ip:10.0.0.1", INICIO)
    repositorio.limpiar("correo:vet@patitas.co")
    assert repositorio.fallos_desde("correo:vet@patitas.co", ANTES) == []
    assert len(repositorio.fallos_desde("ip:10.0.0.1", ANTES)) == 1


def test_purgar_borra_los_fallos_viejos_de_todas_las_claves(repositorio):
    repositorio.registrar_fallo("correo:vet@patitas.co", INICIO)
    repositorio.registrar_fallo("ip:10.0.0.1", INICIO + timedelta(minutes=30))
    repositorio.purgar_antes_de(INICIO + timedelta(minutes=10))
    assert repositorio.fallos_desde("correo:vet@patitas.co", ANTES) == []
    assert len(repositorio.fallos_desde("ip:10.0.0.1", ANTES)) == 1


@pytest.mark.postgres
def test_la_base_rechaza_claves_vacias(bd_limpia):
    with pytest.raises(IntegrityError), bd_limpia.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO intentos_fallidos (clave, ocurrido_en) VALUES ('', now())"))


# --- Servicio --------------------------------------------------------------

def limite(reloj, maximo=5):
    return LimiteIntentos(RepositorioIntentosEnMemoria(), maximo=maximo,
                          ventana=timedelta(minutes=15), reloj=reloj)


def test_bloquea_al_llegar_al_maximo_y_calcula_la_espera():
    reloj = Reloj()
    servicio = limite(reloj)
    for _ in range(4):
        servicio.registrar_fallo(["correo:vet@patitas.co"])
        reloj.avanzar(minutes=1)
    assert servicio.segundos_de_bloqueo(["correo:vet@patitas.co"]) == 0
    servicio.registrar_fallo(["correo:vet@patitas.co"])
    # El primer fallo fue hace 4 minutos: vence en 11 minutos y libera un intento.
    assert servicio.segundos_de_bloqueo(["correo:vet@patitas.co"]) == 11 * 60


def test_el_bloqueo_vence_con_la_ventana():
    reloj = Reloj()
    servicio = limite(reloj)
    for _ in range(5):
        servicio.registrar_fallo(["correo:vet@patitas.co"])
    reloj.avanzar(minutes=15, seconds=1)
    assert servicio.segundos_de_bloqueo(["correo:vet@patitas.co"]) == 0


def test_el_exito_reinicia_la_clave():
    reloj = Reloj()
    servicio = limite(reloj)
    for _ in range(4):
        servicio.registrar_fallo(["correo:vet@patitas.co"])
    servicio.registrar_exito("correo:vet@patitas.co")
    servicio.registrar_fallo(["correo:vet@patitas.co"])
    assert servicio.segundos_de_bloqueo(["correo:vet@patitas.co"]) == 0


def test_cada_clave_tiene_su_propio_maximo():
    reloj = Reloj()
    servicio = LimiteIntentos(RepositorioIntentosEnMemoria(), maximo=5,
                              ventana=timedelta(minutes=15), reloj=reloj,
                              maximos={"ip": 20})
    for _ in range(5):
        servicio.registrar_fallo(["ip:10.0.0.1"])
    assert servicio.segundos_de_bloqueo(["ip:10.0.0.1"]) == 0


@pytest.mark.parametrize("maximo", [0, -1])
def test_maximo_invalido_se_rechaza(maximo):
    with pytest.raises(ValueError):
        limite(Reloj(), maximo=maximo)


# --- API -------------------------------------------------------------------

def app_con_limite(reloj, repositorio_intentos=None):
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    limite_api = LimiteIntentos(repositorio_intentos or RepositorioIntentosEnMemoria(),
                                reloj=reloj)
    app = crear_app(RepositorioEnMemoria(),
                    RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
                    repositorio_usuarios=usuarios, emisor_tokens=EmisorTokens(SECRETO),
                    limite_intentos=limite_api)
    return TestClient(app)


def iniciar_sesion(c, correo="vet@patitas.co", contrasena=CLAVE):
    return c.post("/auth/token", data={"username": correo, "password": contrasena})


def test_sexto_intento_fallido_da_429_con_retry_after():
    c = app_con_limite(Reloj())
    for _ in range(5):
        assert iniciar_sesion(c, contrasena=CLAVE_MALA).status_code == 401
    respuesta = iniciar_sesion(c, contrasena=CLAVE_MALA)
    assert respuesta.status_code == 429
    assert respuesta.headers["Retry-After"] == str(15 * 60)


def test_bloqueado_ni_la_contrasena_correcta_entra():
    """Si la correcta pasara, el atacante sabría que acertó aunque esté bloqueado."""
    c = app_con_limite(Reloj())
    for _ in range(5):
        iniciar_sesion(c, contrasena=CLAVE_MALA)
    assert iniciar_sesion(c).status_code == 429


def test_inicio_correcto_despues_de_la_ventana_funciona():
    reloj = Reloj()
    c = app_con_limite(reloj)
    for _ in range(6):
        iniciar_sesion(c, contrasena=CLAVE_MALA)
    reloj.avanzar(minutes=15, seconds=1)
    assert iniciar_sesion(c).status_code == 200


def test_el_correo_se_normaliza_antes_de_contar():
    c = app_con_limite(Reloj())
    for correo in ("vet@patitas.co", "VET@patitas.co", " Vet@Patitas.co ", "vet@PATITAS.CO",
                   "vet@patitas.co"):
        iniciar_sesion(c, correo=correo, contrasena=CLAVE_MALA)
    assert iniciar_sesion(c).status_code == 429


def test_una_misma_ip_que_prueba_muchos_correos_se_bloquea():
    c = app_con_limite(Reloj())
    for numero in range(20):
        assert iniciar_sesion(c, correo=f"nadie{numero}@patitas.co").status_code == 401
    assert iniciar_sesion(c, correo="otro@patitas.co").status_code == 429


def test_el_bloqueo_de_un_correo_no_afecta_a_otro():
    c = app_con_limite(Reloj())
    for _ in range(5):
        iniciar_sesion(c, correo="coord@patitas.co", contrasena=CLAVE_MALA)
    assert iniciar_sesion(c).status_code == 200


def test_la_contrasena_nunca_aparece_en_el_log(caplog):
    c = app_con_limite(Reloj())
    with caplog.at_level(logging.DEBUG):
        for _ in range(6):
            iniciar_sesion(c, contrasena=CLAVE_MALA)
    assert CLAVE_MALA not in caplog.text
    assert "bloqueado" in caplog.text


@pytest.mark.postgres
def test_el_limite_se_comparte_entre_instancias_con_postgres(bd_limpia):
    """Con PostgreSQL el contador sobrevive a un reinicio y vale para varios procesos."""
    reloj = Reloj()
    primera = app_con_limite(reloj, RepositorioIntentosPostgres(bd_limpia))
    for _ in range(5):
        iniciar_sesion(primera, contrasena=CLAVE_MALA)
    segunda = app_con_limite(reloj, RepositorioIntentosPostgres(bd_limpia))
    assert iniciar_sesion(segunda).status_code == 429
