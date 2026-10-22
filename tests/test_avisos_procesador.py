"""Procesador de avisos (#63, outbox): envía los pendientes, reintenta y deja el estado real."""
from datetime import UTC, datetime, timedelta

from app.avisos.modelos import AvisoNuevo, EstadoAviso
from app.avisos.procesador import ProcesadorAvisos
from app.avisos.repositorio import RepositorioAvisosEnMemoria
from app.notificaciones.correo import EntregaFallida

T0 = datetime(2026, 10, 22, 15, 0, tzinfo=UTC)
ANA = AvisoNuevo("ana@rescate.co", "Rescate crítico ABCD1234 en la comuna 6.")


class Reloj:
    def __init__(self):
        self.ahora = T0

    def __call__(self):
        return self.ahora


class Canal:
    """Doble del correo: falla las primeras «fallas» veces y luego entrega."""

    def __init__(self, fallas=0, permanente=False):
        self.fallas, self.permanente, self.entregados = fallas, permanente, []

    def entregar(self, destinatario, mensaje):
        if self.fallas:
            self.fallas -= 1
            raise EntregaFallida("SMTP: OSError", permanente=self.permanente)
        self.entregados.append(destinatario)


def preparar(canal, **opciones):
    repo, reloj = RepositorioAvisosEnMemoria(), Reloj()
    repo.agregar("ABCD1234", [ANA], T0)
    return repo, reloj, ProcesadorAvisos(repo, canal, reloj=reloj, max_intentos=3,
                                         espera_base_s=60, **opciones)


def estado(repo):
    (aviso,) = repo.de_reporte("ABCD1234")
    return aviso.estado, aviso.intentos, aviso.ultimo_error


def test_envia_el_pendiente_y_queda_enviado():
    canal = Canal()
    repo, _, procesador = preparar(canal)
    assert procesador.procesar() == {"enviados": 1, "reintentos": 0, "fallidos": 0}
    assert canal.entregados == ["ana@rescate.co"]
    assert estado(repo) == (EstadoAviso.ENVIADO, 1, None)


def test_una_falla_temporal_se_reintenta_con_espera_creciente():
    canal = Canal(fallas=2)
    repo, reloj, procesador = preparar(canal)
    assert procesador.procesar()["reintentos"] == 1
    assert estado(repo) == (EstadoAviso.PENDIENTE, 1, "SMTP: OSError")
    reloj.ahora += timedelta(seconds=59)
    assert procesador.procesar() == {"enviados": 0, "reintentos": 0, "fallidos": 0}  # espera
    reloj.ahora += timedelta(seconds=1)
    procesador.procesar()  # 2.º intento falla: ahora espera 120 s
    reloj.ahora += timedelta(seconds=119)
    assert procesador.procesar()["enviados"] == 0
    reloj.ahora += timedelta(seconds=1)
    assert procesador.procesar()["enviados"] == 1
    assert estado(repo) == (EstadoAviso.ENVIADO, 3, None)


def test_se_agotan_los_intentos_y_queda_fallido_sin_ocultarlo():
    repo, reloj, procesador = preparar(Canal(fallas=99))
    for _ in range(3):
        procesador.procesar()
        reloj.ahora += timedelta(hours=1)
    assert estado(repo) == (EstadoAviso.FALLIDO, 3, "SMTP: OSError")
    assert procesador.procesar() == {"enviados": 0, "reintentos": 0, "fallidos": 0}


def test_una_falla_permanente_no_se_reintenta():
    repo, _, procesador = preparar(Canal(fallas=1, permanente=True))
    assert procesador.procesar()["fallidos"] == 1
    assert estado(repo)[0] == EstadoAviso.FALLIDO


def test_un_error_inesperado_del_canal_cuenta_como_falla_temporal():
    class Roto:
        def entregar(self, destinatario, mensaje):
            raise RuntimeError("se cayó la librería")

    repo, _, procesador = preparar(Roto())
    assert procesador.procesar()["reintentos"] == 1
    assert estado(repo) == (EstadoAviso.PENDIENTE, 1, "RuntimeError")


def test_un_canal_sin_entregar_usa_enviar():
    class Viejo:
        def __init__(self):
            self.enviados = []

        def enviar(self, destinatario, mensaje):
            self.enviados.append(destinatario)

    canal = Viejo()
    repo, _, procesador = preparar(canal)
    procesador.procesar()
    assert canal.enviados == ["ana@rescate.co"] and estado(repo)[0] == EstadoAviso.ENVIADO
