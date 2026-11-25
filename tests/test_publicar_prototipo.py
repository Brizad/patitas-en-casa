"""#424: el script que publica los 22 animales del prototipo por la API normal del coordinador.

Se prueba contra la app real en memoria (TestClient), sin red ni credenciales reales.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios
from scripts.operacion import publicar_animales_prototipo as script

CLAVE = "clave-de-prueba-larga"  # falsa
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


class ApiDePrueba(script.Api):
    """La misma clase del script, pero las peticiones van al TestClient."""

    def __init__(self, cliente: TestClient) -> None:
        super().__init__("http://prueba")
        self.c = cliente

    def pedir(self, metodo, ruta, cuerpo=None, tipo=None, espera=120):
        cabeceras = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        if tipo:
            cabeceras["Content-Type"] = tipo
        r = self.c.request(metodo, ruta, content=cuerpo, headers=cabeceras)
        if r.status_code >= 400:
            raise script.ErrorApi(r.status_code, str(r.json().get("detail", "")))
        return r.json() if r.content else None


def preparar(cupo=40):
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    c = TestClient(crear_app(RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("D", cupo)),
                             repositorio_usuarios=usuarios,
                             emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))
    api = ApiDePrueba(c)
    api.entrar("coord@patitas.co", CLAVE)
    return c, api


@pytest.fixture
def fotos(tmp_path) -> Path:
    for a in script.ANIMALES:
        (tmp_path / a.foto).write_bytes(JPEG)
    return tmp_path


def test_los_22_del_prototipo_tienen_datos_validos():
    assert len(script.ANIMALES) == 22
    assert len({a.nombre for a in script.ANIMALES}) == 22
    for a in script.ANIMALES:
        assert len(a.descripcion) >= 20, a.nombre  # RN de la publicación
        assert all(0 <= n <= 100 for n in a.niveles) and len(a.etiquetas) == 3
        assert 0 < a.peso <= a.peso_adulto <= 150


def test_publica_todo_con_ficha_y_foto_y_no_duplica(fotos):
    c, api = preparar()
    lineas = []
    r = script.publicar_todos(api, fotos, lineas.append)
    assert len(r["publicados"]) == 22 and r["saltados"] == [] and r["faltaron"] == []
    catalogo = {a["nombre"]: a for a in c.get("/adopciones/animales").json()}
    toby = catalogo["Toby"]
    assert (toby["carino"], toby["etiquetas"], toby["peso_kg"], toby["peso_adulto_kg"]) == (
        95, ["Juguetón", "Guardián", "Vacunado"], 8, 35)
    assert toby["foto"] and catalogo["Nieve"]["especie"] == "gato"
    # Segunda vez: nada nuevo, nada modificado.
    otra = script.publicar_todos(api, fotos, lineas.append)
    assert otra["publicados"] == [] and len(otra["saltados"]) == 22
    assert len(c.get("/adopciones/animales").json()) == 22


def test_respeta_lo_que_ya_existe(fotos):
    c, api = preparar()
    api.json("POST", "/refugio/ingresos", {"nombre": "Luna", "especie": "perro",
                                           "estado_salud": "sana"})
    r = script.publicar_todos(api, fotos, lambda _: None)
    assert "Luna: ya existe (no se modifica)" in r["saltados"]
    # La Luna que ya estaba (perro) sigue igual y sin publicar: el script no la toca.
    assert all(a["nombre"] != "Luna" for a in c.get("/adopciones/animales").json())


def test_sin_cupo_se_detiene_y_dice_cuales_faltaron(fotos):
    _, api = preparar(cupo=3)
    r = script.publicar_todos(api, fotos, lambda _: None)
    assert [p.split(" ")[0] for p in r["publicados"]] == ["Toby", "Lupe", "Winny"]
    assert len(r["faltaron"]) == 19 and r["faltaron"][0].startswith("Pinina: sin cupo")


def test_una_foto_que_falta_no_detiene_la_publicacion(tmp_path):
    _, api = preparar()
    r = script.publicar_todos(api, tmp_path, lambda _: None)  # carpeta vacía
    assert len(r["publicados"]) == 22 and "sin foto" in r["publicados"][0]
