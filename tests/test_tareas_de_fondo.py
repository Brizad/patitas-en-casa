"""Tareas de fondo de la API (#388): el interruptor PATITAS_TAREAS_DE_FONDO.

Con «0» la API no arranca las tareas periódicas (avisos, escalamientos, videos), así no consulta
la base de Neon mientras nadie la usa. Los avisos quedan pendientes en la base y salen cuando se
vuelve a encender.
"""
import time
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.ajustes import cargar_ajustes_tareas
from app.api.main import crear_app
from app.avisos.modelos import AvisoNuevo, EstadoAviso
from app.avisos.repositorio import RepositorioAvisosEnMemoria
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria

SECRETO_PRUEBAS = "secreto-de-pruebas-con-mas-de-32-caracteres"  # falso, solo pruebas


class NotificadorEspia:
    def __init__(self):
        self.enviados = []

    def enviar(self, destinatario, mensaje):
        self.enviados.append(destinatario)


def _app_con_un_aviso_pendiente(**opciones):
    reportes = RepositorioEnMemoria()
    avisos = RepositorioAvisosEnMemoria()
    avisos.agregar("ABCD1234", [AvisoNuevo("ana@patitas.co", "Rescate crítico")],
                   datetime.now(UTC))
    espia = NotificadorEspia()
    app = crear_app(reportes, RepositorioCuposEnMemoria(Refugio("Demo", capacidad=5)),
                    repositorio_usuarios=RepositorioUsuariosEnMemoria(),
                    emisor_tokens=EmisorTokens(SECRETO_PRUEBAS), notificador=espia,
                    repositorio_avisos=avisos, procesar_avisos_cada_s=0.01, **opciones)
    return app, avisos, espia


def _con_la_app_corriendo(app, segundos=0.3):
    with TestClient(app):  # «with» ejecuta el arranque y el apagado (lifespan)
        time.sleep(segundos)


def test_por_defecto_las_tareas_de_fondo_estan_encendidas(monkeypatch):
    monkeypatch.delenv("PATITAS_TAREAS_DE_FONDO", raising=False)
    assert cargar_ajustes_tareas(None).tareas_de_fondo is True


def test_con_cero_quedan_apagadas(monkeypatch):
    monkeypatch.setenv("PATITAS_TAREAS_DE_FONDO", "0")
    assert cargar_ajustes_tareas(None).tareas_de_fondo is False


def test_apagadas_el_aviso_queda_pendiente_y_no_se_envia(monkeypatch):
    monkeypatch.setenv("PATITAS_TAREAS_DE_FONDO", "0")
    app, avisos, espia = _app_con_un_aviso_pendiente()
    _con_la_app_corriendo(app)
    assert espia.enviados == []
    assert [a.estado for a in avisos.de_reporte("ABCD1234")] == [EstadoAviso.PENDIENTE]


def test_al_encenderlas_sale_el_aviso_que_quedo_pendiente(monkeypatch):
    monkeypatch.setenv("PATITAS_TAREAS_DE_FONDO", "1")
    app, avisos, espia = _app_con_un_aviso_pendiente()
    _con_la_app_corriendo(app)
    assert espia.enviados == ["ana@patitas.co"]
    assert [a.estado for a in avisos.de_reporte("ABCD1234")] == [EstadoAviso.ENVIADO]


def test_el_parametro_de_crear_app_gana_al_entorno(monkeypatch):
    monkeypatch.setenv("PATITAS_TAREAS_DE_FONDO", "1")
    app, _, espia = _app_con_un_aviso_pendiente(tareas_de_fondo=False)
    _con_la_app_corriendo(app)
    assert espia.enviados == []
