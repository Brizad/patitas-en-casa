"""DT-07 (#199): los avisos del escalamiento (RF-23) van al outbox de avisos, con reintentos."""
from app.avisos.modelos import EstadoAviso
from app.avisos.procesador import ProcesadorAvisos
from app.avisos.repositorio import RepositorioAvisosEnMemoria
from app.dominio.modelos import Prioridad
from app.notificaciones.canal import EntregaFallida
from app.rescates.servicio import ServicioRescates
from tests.test_rescates_zona import ANA, LUIS, Escenario


class Canal:
    """Doble del correo: falla las primeras «fallas» veces y luego entrega."""

    def __init__(self, fallas: int = 0) -> None:
        self.fallas, self.entregados = fallas, []

    def entregar(self, destinatario: str, mensaje: str) -> None:
        if self.fallas:
            self.fallas -= 1
            raise EntregaFallida("SMTP: OSError")
        self.entregados.append((destinatario, mensaje))


def escenario():
    e = Escenario()
    e.avisos = RepositorioAvisosEnMemoria()
    e.servicio = ServicioRescates(e.reportes, e.rescates, notificador=e.notificador,
                                  reloj=e.reloj, avisos=e.avisos)
    return e


def test_escalar_guarda_los_avisos_en_el_outbox_y_no_envia_directo():
    e = escenario()
    e.confirmado("COMUNA06", comuna=6)
    e.disponible(LUIS, 2)  # otra zona: se le avisa al ampliar
    e.disponible(ANA, 6)  # de la zona: ya se le avisó al confirmar
    e.reloj.avanzar(minutes=15)
    assert e.servicio.escalar_vencidos() == ["COMUNA06"]
    assert e.notificador.enviados == []  # el envío es del procesador
    por_destino = {a.destinatario: a for a in e.avisos.de_reporte("COMUNA06")}
    assert sorted(por_destino) == ["coordinadores", LUIS]
    assert all(a.estado == EstadoAviso.PENDIENTE for a in por_destino.values())
    assert "COMUNA06" in por_destino["coordinadores"].mensaje
    assert "15 min" in por_destino["coordinadores"].mensaje


def test_si_el_correo_falla_el_aviso_al_coordinador_se_reintenta_y_llega():
    e = escenario()
    e.confirmado("ESPERA01")
    e.reloj.avanzar(minutes=15)
    e.servicio.escalar_vencidos()
    canal = Canal(fallas=1)
    procesador = ProcesadorAvisos(e.avisos, canal, reloj=e.reloj, espera_base_s=60)
    assert procesador.procesar()["reintentos"] == 1
    assert canal.entregados == []
    e.reloj.avanzar(seconds=60)
    assert procesador.procesar()["enviados"] == 1
    assert [d for d, _ in canal.entregados] == ["coordinadores"]
    assert e.avisos.de_reporte("ESPERA01")[0].estado == EstadoAviso.ENVIADO


def test_escalar_dos_veces_no_duplica_los_avisos():
    e = escenario()
    e.confirmado("ESPERA01", prioridad=Prioridad.ALTA)
    e.reloj.avanzar(minutes=30)
    e.servicio.escalar_vencidos()
    e.servicio.escalar_vencidos()
    assert len(e.avisos.de_reporte("ESPERA01")) == 1


def test_sin_outbox_se_conserva_el_envio_directo():
    e = Escenario()  # sin repositorio de avisos
    e.confirmado("ESPERA01")
    e.reloj.avanzar(minutes=15)
    e.servicio.escalar_vencidos()
    assert len(e.notificador.para("coordinadores")) == 1


def test_si_el_outbox_falla_el_reporte_no_queda_escalado_y_se_reintenta():
    e = escenario()

    class OutboxRoto(RepositorioAvisosEnMemoria):
        roto = True

        def agregar(self, codigo, avisos, ahora):
            if self.roto:
                raise OSError("base caída")
            return super().agregar(codigo, avisos, ahora)

    e.avisos = OutboxRoto()
    e.servicio = ServicioRescates(e.reportes, e.rescates, reloj=e.reloj, avisos=e.avisos)
    e.confirmado("ESPERA01")
    e.reloj.avanzar(minutes=15)
    try:
        e.servicio.escalar_vencidos()
    except OSError:
        pass
    assert e.rescates.escalados() == set()  # no se marca: la próxima revisión lo reintenta
    e.avisos.roto = False
    assert e.servicio.escalar_vencidos() == ["ESPERA01"]
    assert [a.destinatario for a in e.avisos.de_reporte("ESPERA01")] == ["coordinadores"]
