"""El video espera en PostgreSQL (#188): sobrevive al reinicio, se borra y respeta los límites."""
import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app import config
from app.video.almacen import MAX_BYTES, AlmacenEnPostgres, ArchivoInvalido

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x07" * 100


async def _trozos(*partes):
    for parte in partes:
        yield parte


def guardar(almacen, *partes):
    return asyncio.run(almacen.guardar(_trozos(*partes)))


@pytest.fixture
def almacen(bd_limpia):
    return AlmacenEnPostgres(bd_limpia)


def contenido(almacen, ruta):
    return b"".join(almacen.leer(ruta))


@pytest.mark.postgres
def test_guarda_en_trozos_y_devuelve_el_mismo_video(almacen, monkeypatch):
    monkeypatch.setattr(config, "TROZO_VIDEO_BYTES", 64)
    video = MP4 + b"\x01" * 300
    ruta, tamano = guardar(almacen, video[:50], video[50:200], video[200:])
    assert tamano == len(video) and almacen.existe(ruta)
    assert contenido(almacen, ruta) == video


@pytest.mark.postgres
def test_sobrevive_a_un_reinicio_otra_instancia_lo_lee(almacen, bd_limpia):
    ruta, _ = guardar(almacen, MP4)
    nueva = AlmacenEnPostgres(bd_limpia)  # el proceso se reinició
    assert nueva.existe(ruta) and contenido(nueva, ruta) == MP4


@pytest.mark.postgres
def test_borrar_libera_el_espacio(almacen):
    ruta, _ = guardar(almacen, MP4)
    almacen.borrar(ruta)
    assert not almacen.existe(ruta) and contenido(almacen, ruta) == b""


@pytest.mark.postgres
def test_un_archivo_que_no_es_video_no_deja_nada(almacen):
    with pytest.raises(ArchivoInvalido):
        guardar(almacen, b"%PDF-1.4 no soy un video" + b"\x00" * 100)
    assert almacen.purgar_antes_de(datetime.now(UTC) + timedelta(days=1)) == 0


@pytest.mark.postgres
def test_pasar_de_50_mb_se_rechaza_y_se_borra_lo_escrito(almacen, monkeypatch):
    monkeypatch.setattr("app.video.almacen.MAX_BYTES", 150)
    monkeypatch.setattr(config, "TROZO_VIDEO_BYTES", 64)
    assert MAX_BYTES == config.VIDEO_MAX_MB * 1024 * 1024
    with pytest.raises(ArchivoInvalido, match="MB"):
        guardar(almacen, MP4, b"\x00" * 200)
    assert almacen.purgar_antes_de(datetime.now(UTC) + timedelta(days=1)) == 0


@pytest.mark.postgres
def test_purgar_borra_solo_los_huerfanos_viejos(almacen):
    vieja, _ = guardar(almacen, MP4)
    ahora, _ = guardar(almacen, MP4)
    assert almacen.purgar_antes_de(datetime.now(UTC) - timedelta(hours=1)) == 0
    assert almacen.purgar_antes_de(datetime.now(UTC) + timedelta(seconds=1)) == 2
    assert not almacen.existe(vieja) and not almacen.existe(ahora)
