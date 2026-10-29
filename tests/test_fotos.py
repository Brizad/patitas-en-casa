"""RF-25 (#115): fotos de los animales en adopción, validadas por su contenido."""
import pytest

from app.adopciones.fotos import (
    MAX_BYTES,
    FotoInvalida,
    RepositorioFotosEnMemoria,
    tipo_de_imagen,
)
from app.adopciones.fotos_postgres import RepositorioFotosPostgres
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Animal, Especie
from tests.test_decision_adopcion import en_memoria, h, preparar

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


def test_el_tipo_se_decide_por_el_contenido():
    assert tipo_de_imagen(PNG) == "image/png"
    assert tipo_de_imagen(JPEG) == "image/jpeg"
    assert tipo_de_imagen(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    with pytest.raises(FotoInvalida, match="JPEG"):
        tipo_de_imagen(b"<html><script>alert(1)</script>")
    with pytest.raises(FotoInvalida, match="KB"):
        tipo_de_imagen(JPEG + b"\x00" * MAX_BYTES)


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repos(request):
    if request.param == "postgres":
        motor = request.getfixturevalue("bd_limpia")
        animal = Animal("Luna", Especie.PERRO, "sana")
        RepositorioCuposPostgres.primer_refugio(motor).ocupar_cupo(animal)
        return RepositorioFotosPostgres(motor), animal.id
    return RepositorioFotosEnMemoria(), 1


def test_contrato_una_foto_por_animal(repos):
    fotos, animal_id = repos
    assert fotos.foto(animal_id) is None and fotos.con_foto() == set()
    fotos.guardar(animal_id, "image/png", PNG)
    fotos.guardar(animal_id, "image/jpeg", JPEG)  # la reemplaza
    assert fotos.foto(animal_id) == ("image/jpeg", JPEG)
    assert fotos.con_foto() == {animal_id}


def test_api_subir_y_ver_la_foto_en_el_catalogo():
    c = en_memoria()
    coord, animal_id, _ = preparar(c)
    ruta = f"/refugio/animales/{animal_id}/foto"
    subir = c.post(ruta, files={"foto": ("canela.jpg", JPEG, "image/jpeg")}, headers=coord)
    assert subir.status_code == 201
    (publicado,) = c.get("/adopciones/animales").json()
    assert publicado["foto"] == f"/adopciones/animales/{animal_id}/foto"
    foto = c.get(publicado["foto"])  # pública, como el catálogo
    assert foto.status_code == 200 and foto.content == JPEG
    assert foto.headers["content-type"] == "image/jpeg"
    assert foto.headers["x-content-type-options"] == "nosniff"


def test_api_rechaza_archivos_que_no_son_fotos_y_otros_roles():
    c = en_memoria()
    coord, animal_id, _ = preparar(c)
    ruta = f"/refugio/animales/{animal_id}/foto"
    falsa = c.post(ruta, files={"foto": ("x.jpg", b"<script>", "image/jpeg")}, headers=coord)
    assert falsa.status_code == 415
    assert c.post(ruta, files={"foto": ("x.jpg", JPEG, "image/jpeg")}).status_code == 401
    assert c.post(ruta, files={"foto": ("x.jpg", JPEG, "image/jpeg")},
                  headers=h(c, "lau@correo.co")).status_code == 403
    assert c.post("/refugio/animales/999/foto", files={"foto": ("x.jpg", JPEG, "image/jpeg")},
                  headers=coord).status_code == 404
    assert c.get(f"/adopciones/animales/{animal_id}/foto").status_code == 404
