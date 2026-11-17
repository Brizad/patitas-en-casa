"""Adaptador de Mailjet (P-08) contra un servidor HTTP falso: sin red externa."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.ajustes import ConfiguracionIncompleta, cargar_ajustes_correo
from app.notificaciones.correo import (
    EntregaFallida,
    NotificadorCorreo,
    NotificadorRegistro,
    crear_notificador,
)
from app.notificaciones.mailjet import NotificadorMailjet


@pytest.fixture
def servidor():
    """Servidor falso: responde lo que diga `respuesta` y guarda las peticiones."""
    recibidas: list[dict] = []
    respuesta = {"estado": 200, "cuerpo": {"Messages": [{"Status": "success"}]}}

    class Manejador(BaseHTTPRequestHandler):
        def do_POST(self):
            largo = int(self.headers["Content-Length"])
            recibidas.append({"ruta": self.path, "auth": self.headers["Authorization"],
                              "json": json.loads(self.rfile.read(largo))})
            self.send_response(respuesta["estado"])
            self.end_headers()
            self.wfile.write(json.dumps(respuesta["cuerpo"]).encode())

        def log_message(self, *args):
            pass

    http = HTTPServer(("127.0.0.1", 0), Manejador)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{http.server_port}/v3.1/send", recibidas, respuesta
    http.shutdown()
    http.server_close()


def notificador(url, grupos=None):
    return NotificadorMailjet("llave", "secreto", "alertas@prueba.local",
                              grupos if grupos is not None else {}, url=url)


def test_envia_a_una_persona_con_autenticacion_basica(servidor):
    url, recibidas, _ = servidor
    notificador(url).entregar("rescata@prueba.local", "Caso crítico en tu zona")
    peticion = recibidas[0]
    assert peticion["ruta"] == "/v3.1/send"
    assert peticion["auth"] == "Basic " + base64.b64encode(b"llave:secreto").decode()
    mensaje = peticion["json"]["Messages"][0]
    assert mensaje["From"]["Email"] == "alertas@prueba.local"
    assert mensaje["To"] == [{"Email": "rescata@prueba.local"}]
    assert "Caso crítico" in mensaje["Subject"] and "Caso crítico" in mensaje["TextPart"]


def test_un_grupo_se_expande_a_sus_correos(servidor):
    url, recibidas, _ = servidor
    n = notificador(url, {"coordinadores": ["a@prueba.local", "b@prueba.local"]})
    n.entregar("coordinadores", "Ocupación sobre el 90 %")
    assert recibidas[0]["json"]["Messages"][0]["To"] == [
        {"Email": "a@prueba.local"}, {"Email": "b@prueba.local"}]


def test_grupo_sin_correos_es_falla_permanente(servidor):
    url, recibidas, _ = servidor
    with pytest.raises(EntregaFallida) as error:
        notificador(url).entregar("coordinadores", "x")
    assert error.value.permanente and recibidas == []


@pytest.mark.parametrize("estado,permanente",
                         [(400, True), (422, True), (401, False), (429, False), (500, False)])
def test_errores_http_marcan_si_reintentar_ayuda(servidor, estado, permanente):
    url, _, respuesta = servidor
    respuesta["estado"] = estado
    with pytest.raises(EntregaFallida) as error:
        notificador(url).entregar("a@prueba.local", "x")
    assert error.value.permanente is permanente
    assert str(estado) in str(error.value)


def test_respuesta_200_sin_success_es_falla(servidor):
    url, _, respuesta = servidor
    respuesta["cuerpo"] = {"Messages": [{"Status": "error"}]}
    with pytest.raises(EntregaFallida):
        notificador(url).entregar("a@prueba.local", "x")


def test_sin_conexion_es_falla_reintentable_sin_datos_de_la_cuenta():
    with pytest.raises(EntregaFallida) as error:
        notificador("http://127.0.0.1:1/v3.1/send").entregar("a@prueba.local", "x")
    assert not error.value.permanente
    assert "llave" not in str(error.value) and "secreto" not in str(error.value)


def test_enviar_no_propaga_la_falla(servidor, caplog):
    url, _, respuesta = servidor
    respuesta["estado"] = 500
    notificador(url).enviar("a@prueba.local", "Alerta")
    assert "No se pudo enviar" in caplog.text


@pytest.fixture
def entorno(monkeypatch):
    for v in ["SMTP_HOST", "SMTP_REMITENTE", "MAILJET_API_KEY", "MAILJET_SECRET_KEY",
              "CORREO_REMITENTE"]:
        monkeypatch.delenv(f"PATITAS_{v}", raising=False)
    return monkeypatch


def test_con_claves_de_mailjet_se_usa_mailjet_aunque_haya_smtp(entorno):
    entorno.setenv("PATITAS_SMTP_HOST", "smtp.prueba.local")
    entorno.setenv("PATITAS_SMTP_REMITENTE", "a@prueba.local")
    entorno.setenv("PATITAS_MAILJET_API_KEY", "k")
    entorno.setenv("PATITAS_MAILJET_SECRET_KEY", "s")
    entorno.setenv("PATITAS_CORREO_REMITENTE", "alertas@prueba.local")
    assert isinstance(crear_notificador(cargar_ajustes_correo(archivo_env=None)),
                      NotificadorMailjet)


def test_con_una_sola_clave_de_mailjet_sigue_el_camino_de_antes(entorno):
    entorno.setenv("PATITAS_MAILJET_API_KEY", "k")
    assert isinstance(crear_notificador(cargar_ajustes_correo(archivo_env=None)),
                      NotificadorRegistro)
    entorno.setenv("PATITAS_SMTP_HOST", "smtp.prueba.local")
    entorno.setenv("PATITAS_SMTP_REMITENTE", "a@prueba.local")
    assert isinstance(crear_notificador(cargar_ajustes_correo(archivo_env=None)),
                      NotificadorCorreo)


def test_mailjet_sin_remitente_es_configuracion_incompleta(entorno):
    entorno.setenv("PATITAS_MAILJET_API_KEY", "k")
    entorno.setenv("PATITAS_MAILJET_SECRET_KEY", "s")
    with pytest.raises(ConfiguracionIncompleta):
        crear_notificador(cargar_ajustes_correo(archivo_env=None))


def test_las_claves_de_mailjet_no_aparecen_al_imprimir_los_ajustes(entorno):
    entorno.setenv("PATITAS_MAILJET_API_KEY", "llave-falsa-mj")
    entorno.setenv("PATITAS_MAILJET_SECRET_KEY", "secreto-falso-mj")
    texto = repr(cargar_ajustes_correo(archivo_env=None))
    assert "llave-falsa-mj" not in texto and "secreto-falso-mj" not in texto


def test_rechaza_url_sin_https():
    import pytest

    from app.notificaciones.mailjet import NotificadorMailjet
    for url in ["file:///etc/passwd", "http://api.mailjet.com/v3.1/send", "ftp://x"]:
        with pytest.raises(ValueError):
            NotificadorMailjet("k", "s", "a@b.co", {}, url=url)
