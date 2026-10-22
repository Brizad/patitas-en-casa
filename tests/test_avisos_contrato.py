"""Contrato de RepositorioAvisos (#63, outbox): memoria y PostgreSQL pasan las mismas pruebas."""
import threading
from datetime import UTC, datetime, timedelta

import pytest

from app.avisos.modelos import AvisoNuevo, EstadoAviso
from app.avisos.repositorio import RepositorioAvisosEnMemoria, resumen
from app.avisos.repositorio_postgres import RepositorioAvisosPostgres
from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.reportes.repositorio_postgres import RepositorioPostgres

T0 = datetime(2026, 10, 22, 15, 0, tzinfo=UTC)
VENCE = timedelta(minutes=5)
ANA = AvisoNuevo("ana@rescate.co", "Rescate crítico ABCD1234 en la comuna 6.")
LUIS = AvisoNuevo("luis@rescate.co", "Rescate crítico ABCD1234 en la comuna 6.")


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repo(request):
    if request.param == "memoria":
        return RepositorioAvisosEnMemoria()
    motor = request.getfixturevalue("bd_limpia")
    RepositorioPostgres(motor).guardar(Reporte(
        codigo="ABCD1234", descripcion="Perro atropellado frente al parque",
        ubicacion=Ubicacion(direccion="Calle 10", comuna=6), prioridad=Prioridad.CRITICA,
        confianza=0.8, estado=EstadoReporte.CONFIRMADO))
    return RepositorioAvisosPostgres(motor)


def test_agregar_deja_los_avisos_pendientes_e_ignora_repetidos(repo):
    assert repo.agregar("ABCD1234", [ANA, LUIS], T0) == 2
    assert repo.agregar("ABCD1234", [ANA], T0) == 0
    avisos = repo.de_reporte("ABCD1234")
    assert [(a.destinatario, a.estado, a.intentos) for a in avisos] == [
        ("ana@rescate.co", EstadoAviso.PENDIENTE, 0), ("luis@rescate.co", EstadoAviso.PENDIENTE, 0)]
    assert resumen(avisos) == {"pendiente": 2, "enviando": 0, "enviado": 0, "fallido": 0}


def test_reclamar_marca_enviando_suma_un_intento_y_no_repite(repo):
    repo.agregar("ABCD1234", [ANA, LUIS], T0)
    (primero,) = repo.reclamar(T0, limite=1, vencimiento=VENCE)
    assert (primero.destinatario, primero.estado, primero.intentos) == (
        "ana@rescate.co", EstadoAviso.ENVIANDO, 1)
    (segundo,) = repo.reclamar(T0, limite=5, vencimiento=VENCE)
    assert segundo.destinatario == "luis@rescate.co"
    assert repo.reclamar(T0, limite=5, vencimiento=VENCE) == []


def test_enviado_y_fallo_con_reintento_programado(repo):
    repo.agregar("ABCD1234", [ANA, LUIS], T0)
    ana, luis = repo.reclamar(T0, limite=5, vencimiento=VENCE)
    repo.marcar_enviado(ana.id, T0)
    repo.marcar_fallo(luis.id, "SMTP: OSError", T0 + timedelta(minutes=1))
    assert repo.reclamar(T0, limite=5, vencimiento=VENCE) == []  # aún no toca reintentar
    (otra_vez,) = repo.reclamar(T0 + timedelta(minutes=1), limite=5, vencimiento=VENCE)
    assert (otra_vez.destinatario, otra_vez.intentos, otra_vez.ultimo_error) == (
        "luis@rescate.co", 2, "SMTP: OSError")
    enviado = repo.de_reporte("ABCD1234")[0]
    assert (enviado.estado, enviado.enviado_en) == (EstadoAviso.ENVIADO, T0)


def test_sin_proximo_intento_queda_fallido_y_no_se_reclama(repo):
    repo.agregar("ABCD1234", [ANA], T0)
    (ana,) = repo.reclamar(T0, limite=5, vencimiento=VENCE)
    repo.marcar_fallo(ana.id, "No hay correos configurados", None)
    assert repo.reclamar(T0 + timedelta(days=1), limite=5, vencimiento=VENCE) == []
    assert repo.de_reporte("ABCD1234")[0].estado == EstadoAviso.FALLIDO


def test_un_reclamo_vencido_se_recupera_y_puede_reenviar(repo):
    """Si el procesador se detuvo después de reclamar, el aviso vuelve a reclamarse al
    vencer: no se pierde, pero puede enviarse dos veces (al menos una vez, no exactamente una)."""
    repo.agregar("ABCD1234", [ANA], T0)
    repo.reclamar(T0, limite=5, vencimiento=VENCE)
    assert repo.reclamar(T0 + VENCE, limite=5, vencimiento=VENCE) == []
    (recuperado,) = repo.reclamar(T0 + VENCE + timedelta(seconds=1), limite=5,
                                  vencimiento=VENCE)
    assert recuperado.intentos == 2


def test_dos_procesadores_a_la_vez_no_reclaman_el_mismo_aviso(repo):
    repo.agregar("ABCD1234", [AvisoNuevo(f"r{i}@rescate.co", "m") for i in range(10)], T0)
    barrera, reclamados = threading.Barrier(2), []

    def procesador():
        barrera.wait()
        reclamados.extend(a.id for a in repo.reclamar(T0, limite=10, vencimiento=VENCE))

    hilos = [threading.Thread(target=procesador) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(reclamados) == sorted(set(reclamados)) and len(reclamados) == 10
