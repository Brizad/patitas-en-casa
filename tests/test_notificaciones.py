"""Notificaciones reales detrás de la interfaz Notificador (DT-03, HU-06)."""
import logging
import smtplib

import pytest

from app.ajustes import cargar_ajustes_correo
from app.cupos.servicio import ServicioCupos
from app.dominio.modelos import Animal, Especie, Refugio
from app.notificaciones.correo import NotificadorCorreo, NotificadorRegistro, crear_notificador

VARIABLES = ["PATITAS_SMTP_HOST", "PATITAS_SMTP_PORT", "PATITAS_SMTP_USUARIO",
             "PATITAS_SMTP_CONTRASENA", "PATITAS_SMTP_REMITENTE", "PATITAS_SMTP_STARTTLS",
             "PATITAS_CORREOS_COORDINADORES"]


class SMTPFalso:
    """Reemplaza smtplib.SMTP: guarda lo que se habría enviado, sin red."""
    enviados: list = []
    conexiones: list = []

    def __init__(self, host, port, timeout):
        SMTPFalso.conexiones.append({"host": host, "port": port, "timeout": timeout,
                                     "starttls": False, "login": None})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        SMTPFalso.conexiones[-1]["starttls"] = True

    def login(self, usuario, contrasena):
        SMTPFalso.conexiones[-1]["login"] = usuario

    def send_message(self, mensaje):
        SMTPFalso.enviados.append(mensaje)


class SMTPCaido(SMTPFalso):
    def __init__(self, host, port, timeout):
        raise OSError("servidor de correo no disponible")


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for variable in VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    SMTPFalso.enviados, SMTPFalso.conexiones = [], []
    monkeypatch.setattr(smtplib, "SMTP", SMTPFalso)


def correo(**cambios):
    datos = {"host": "smtp.prueba.local", "puerto": 587, "usuario": "alertas@prueba.local",
             "contrasena": "clave-falsa-smtp", "remitente": "alertas@prueba.local",
             "starttls": True, "grupos": {"coordinadores": ["coord1@prueba.local",
                                                            "coord2@prueba.local"]}}
    return NotificadorCorreo(**{**datos, **cambios})


def test_envia_el_correo_a_todo_el_grupo():
    correo().enviar("coordinadores", "Ocupación sobre el 90 % en Refugio demo Cúcuta")
    (mensaje,) = SMTPFalso.enviados
    assert mensaje["To"] == "coord1@prueba.local, coord2@prueba.local"
    assert mensaje["From"] == "alertas@prueba.local"
    assert "Ocupación sobre el 90 %" in mensaje["Subject"]
    assert "Refugio demo Cúcuta" in mensaje.get_content()


def test_un_destinatario_con_arroba_recibe_el_correo_directo():
    """HU-06 (#46): la alerta de rescate va al correo de cada rescatista."""
    correo().enviar("ana@rescate.co", "Rescate crítico F2HW5RTB en la comuna 6.")
    (mensaje,) = SMTPFalso.enviados
    assert mensaje["To"] == "ana@rescate.co"


def test_usa_starttls_login_y_tiempo_maximo():
    correo().enviar("coordinadores", "Alerta")
    (conexion,) = SMTPFalso.conexiones
    assert conexion == {"host": "smtp.prueba.local", "port": 587, "timeout": 10,
                        "starttls": True, "login": "alertas@prueba.local"}


def test_sin_usuario_no_hace_login():
    correo(usuario=None, contrasena=None).enviar("coordinadores", "Alerta")
    assert SMTPFalso.conexiones[0]["login"] is None


def test_si_el_correo_falla_no_rompe_el_ingreso_y_queda_en_el_log(monkeypatch, caplog):
    monkeypatch.setattr(smtplib, "SMTP", SMTPCaido)
    with caplog.at_level(logging.ERROR):
        correo().enviar("coordinadores", "Alerta")  # no lanza excepción
    assert "No se pudo enviar" in caplog.text
    assert "clave-falsa-smtp" not in caplog.text


def test_grupo_sin_destinatarios_se_registra_y_no_envia(caplog):
    with caplog.at_level(logging.WARNING):
        correo(grupos={}).enviar("coordinadores", "Alerta")
    assert SMTPFalso.enviados == []
    assert "coordinadores" in caplog.text


def test_notificador_de_registro_escribe_en_el_log(caplog):
    with caplog.at_level(logging.WARNING):
        NotificadorRegistro().enviar("coordinadores", "Ocupación sobre el 90 %")
    assert "coordinadores" in caplog.text and "90 %" in caplog.text


def test_sin_smtp_configurado_se_usa_el_registro():
    assert isinstance(crear_notificador(cargar_ajustes_correo(archivo_env=None)),
                      NotificadorRegistro)


def test_con_smtp_configurado_se_usa_el_correo(monkeypatch):
    monkeypatch.setenv("PATITAS_SMTP_HOST", "smtp.prueba.local")
    monkeypatch.setenv("PATITAS_SMTP_REMITENTE", "alertas@prueba.local")
    monkeypatch.setenv("PATITAS_CORREOS_COORDINADORES", "a@prueba.local, b@prueba.local")
    notificador = crear_notificador(cargar_ajustes_correo(archivo_env=None))
    notificador.enviar("coordinadores", "Alerta")
    assert SMTPFalso.enviados[0]["To"] == "a@prueba.local, b@prueba.local"


def test_la_contrasena_smtp_no_aparece_al_imprimir_los_ajustes(monkeypatch):
    monkeypatch.setenv("PATITAS_SMTP_HOST", "smtp.prueba.local")
    monkeypatch.setenv("PATITAS_SMTP_CONTRASENA", "clave-falsa-smtp")
    assert "clave-falsa-smtp" not in repr(cargar_ajustes_correo(archivo_env=None))


def test_crear_app_usa_el_notificador_inyectado():
    """Por la API: el ingreso que deja el refugio en 36/40 (90 %) alerta a coordinación."""
    from fastapi.testclient import TestClient

    from app.api.main import crear_app
    from app.cupos.repositorio import RepositorioCuposEnMemoria
    from app.dominio.modelos import Rol
    from app.reportes.repositorio import RepositorioEnMemoria
    from app.seguridad.tokens import EmisorTokens
    from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
    from app.usuarios.servicio import ServicioUsuarios

    clave = "clave-de-prueba-larga"  # falsa
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, clave)
    c = TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40, 35)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres"),
        notificador=correo()))
    token = c.post("/auth/token", data={"username": "coord@patitas.co", "password": clave})
    c.post("/refugio/ingresos", json={"nombre": "Luna", "especie": "perro",
                                      "estado_salud": "herida en pata"},
           headers={"Authorization": f"Bearer {token.json()['access_token']}"})
    assert len(SMTPFalso.enviados) == 1


def test_rn04_la_alerta_del_90_por_ciento_llega_por_correo():
    """De punta a punta: el ingreso que llega al 90 % envía el correo a coordinación."""
    servicio = ServicioCupos(Refugio("Refugio demo Cúcuta", 40, 35), correo())
    servicio.registrar_ingreso(Animal("Luna", Especie.PERRO, "herida en pata"))
    (mensaje,) = SMTPFalso.enviados
    assert "90 %" in mensaje["Subject"]
