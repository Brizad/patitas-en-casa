"""Tareas de fondo de la API (#388): el interruptor PATITAS_TAREAS_DE_FONDO.

Con «0» la API no arranca las tareas periódicas (avisos, escalamientos, videos), así no consulta
la base de Neon mientras nadie la usa. Los avisos quedan pendientes en la base y salen cuando se
vuelve a encender.
"""
import asyncio
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
from app.tareas_de_fondo import Reposo, TareaDeFondo
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


# --- #390: la tarea solo revisa cuando hay trabajo --------------------------------

def _correr(tarea, hasta, *, despertar_cuando=None, limite_s=5.0):
    """Corre la tarea hasta que «hasta()» sea cierto (o falle por tiempo) y la detiene."""
    async def principal():
        corriendo = asyncio.create_task(tarea.correr())
        while not hasta():
            if despertar_cuando and despertar_cuando():
                tarea.despertar()
            await asyncio.sleep(0.005)
        corriendo.cancel()
    asyncio.run(asyncio.wait_for(principal(), timeout=limite_s))


def test_sin_trabajo_y_sin_reposo_revisa_una_vez_y_duerme():
    revisiones = []
    tarea = TareaDeFondo("prueba", lambda: revisiones.append(1))  # devuelve None
    _correr(tarea, lambda: len(tarea.esperas) == 1)
    time.sleep(0.05)
    assert revisiones == [1] and tarea.esperas == [None]  # None: hasta que la despierten


def test_despertarla_provoca_otra_revision():
    revisiones = []
    tarea = TareaDeFondo("prueba", lambda: revisiones.append(1))
    _correr(tarea, lambda: len(revisiones) >= 2, despertar_cuando=lambda: len(revisiones) == 1)
    assert len(revisiones) >= 2  # sin despertarla se habría quedado en 1


def test_la_revision_decide_cuando_vuelve():
    tarea = TareaDeFondo("prueba", lambda: 0.01)
    _correr(tarea, lambda: len(tarea.esperas) >= 3)
    assert tarea.esperas[:3] == [0.01, 0.01, 0.01]


def test_el_reposo_crece_hasta_el_tope():
    tarea = TareaDeFondo("prueba", lambda: None, reposo=Reposo(0.001, 0.004))
    _correr(tarea, lambda: len(tarea.esperas) >= 5)
    assert tarea.esperas[:5] == [0.001, 0.002, 0.004, 0.004, 0.004]


def test_tras_un_error_reintenta_con_espera_creciente():
    def falla():
        raise RuntimeError("base caída")
    tarea = TareaDeFondo("prueba", falla, tras_error=Reposo(0.001, 0.002))
    _correr(tarea, lambda: len(tarea.esperas) >= 3)
    assert tarea.esperas[:3] == [0.001, 0.002, 0.002]


class Contador:
    """Envuelve un repositorio y cuenta las llamadas (cada una sería una consulta)."""

    def __init__(self, real):
        self._real, self.llamadas = real, 0

    def __getattr__(self, nombre):
        atributo = getattr(self._real, nombre)
        if not callable(atributo):
            return atributo

        def contado(*args, **kwargs):
            self.llamadas += 1
            return atributo(*args, **kwargs)
        return contado


def test_en_reposo_las_tareas_no_consultan_la_base(monkeypatch):
    """Con los valores de producción: tras la revisión del arranque, nada más hasta que
    alguien haga algo. Antes había una consulta de avisos cada 15 s."""
    monkeypatch.setenv("PATITAS_TAREAS_DE_FONDO", "1")
    reportes, avisos = Contador(RepositorioEnMemoria()), Contador(RepositorioAvisosEnMemoria())
    app = crear_app(reportes, RepositorioCuposEnMemoria(Refugio("Demo", capacidad=5)),
                    repositorio_usuarios=RepositorioUsuariosEnMemoria(),
                    emisor_tokens=EmisorTokens(SECRETO_PRUEBAS), notificador=NotificadorEspia(),
                    repositorio_avisos=avisos)
    with TestClient(app) as c:
        time.sleep(0.3)  # la revisión del arranque
        despues_del_arranque = (reportes.llamadas, avisos.llamadas)
        assert despues_del_arranque[1] >= 1  # sí revisó al arrancar
        time.sleep(0.5)
        assert (reportes.llamadas, avisos.llamadas) == despues_del_arranque
        # Avisos: reposo desde 15 s. Escalamientos: sin rescates ofrecidos, hasta que la
        # despierten (None). Sin token de video no hay tarea de videos.
        assert [t.esperas for t in app.state.tareas_de_fondo] == [[15], [None]]
        # Un reporte nuevo (petición que cambia datos) las despierta.
        assert c.post("/reportes", json={"descripcion": "Perro herido en la calle 10 del centro",
                                         "direccion": "Calle 10"}).status_code == 201
        time.sleep(0.3)
        assert avisos.llamadas > despues_del_arranque[1]
