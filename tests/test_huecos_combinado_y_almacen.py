"""Huecos que dejó la medición de cobertura y de mutantes (PLAN_CIERRE, trabajo 4d).

Cada prueba fija una regla que antes nadie vigilaba: el triaje no se cae si el modelo no carga
(RN-03, RNF-03) y el video que pasa del tope o no es un video se borra del disco (RN-01).
"""
import asyncio

import pytest

from app.triaje import combinado
from app.triaje.clasificador import VERSION, clasificar
from app.video.almacen import AlmacenEnDisco, ArchivoInvalido, es_video

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20


async def _trozos(*partes: bytes):
    for parte in partes:
        yield parte


def _guardar(almacen: AlmacenEnDisco, *partes: bytes):
    return asyncio.run(almacen.guardar(_trozos(*partes)))


# --- Triaje: el modelo nunca tumba al clasificador ------------------------------------------

def test_si_el_modelo_no_carga_se_sigue_solo_con_reglas(monkeypatch):
    def no_carga():
        raise OSError("modelo ausente")

    monkeypatch.setattr(combinado, "cargar_modelo", no_carga)
    clasificador, version = combinado.triaje_por_defecto()
    assert clasificador is clasificar
    assert version == VERSION  # la versión guardada dice que no hubo modelo (RF-20)


def test_con_modelo_la_version_guardada_incluye_la_del_modelo(monkeypatch):
    class ModeloFalso:
        version = "m-prueba"

    monkeypatch.setattr(combinado, "cargar_modelo", lambda: ModeloFalso())
    _, version = combinado.triaje_por_defecto()
    assert version == f"{VERSION}+m-prueba"


def test_una_evidencia_del_modelo_sin_comillas_no_repite_ninguna_senal():
    senales = ["señal 'sarna' -> baja"]
    assert combinado._repite_senal("texto sin término entre comillas", senales) is False
    assert combinado._repite_senal("«sarna» apunta a baja", senales) is True


# --- Video: lo que no sirve no se queda en el disco -----------------------------------------

def test_un_video_valido_se_guarda_y_se_puede_leer(tmp_path):
    almacen = AlmacenEnDisco(tmp_path)
    ruta, tamano = _guardar(almacen, MP4[:10], MP4[10:])
    assert tamano == len(MP4)
    assert almacen.existe(ruta)
    assert b"".join(almacen.leer(ruta)) == MP4


def test_si_pasa_del_tope_se_rechaza_y_no_deja_archivo(tmp_path):
    almacen = AlmacenEnDisco(tmp_path, max_bytes=16)
    with pytest.raises(ArchivoInvalido, match="pasa de"):
        _guardar(almacen, MP4)
    assert list(tmp_path.iterdir()) == []


def test_si_no_es_un_video_se_rechaza_y_no_deja_archivo(tmp_path):
    almacen = AlmacenEnDisco(tmp_path)
    with pytest.raises(ArchivoInvalido, match="no es un video"):
        _guardar(almacen, b"%PDF-1.7 esto no es un video, es un documento")
    assert list(tmp_path.iterdir()) == []


def test_las_firmas_de_mp4_mov_y_webm_son_videos_y_otras_no():
    assert es_video(MP4)
    assert es_video(b"\x1a\x45\xdf\xa3" + b"\x00" * 8)
    assert not es_video(b"GIF89a" + b"\x00" * 8)


def test_borrar_un_archivo_que_ya_no_existe_no_falla_y_purgar_no_borra_nada(tmp_path):
    from datetime import UTC, datetime

    almacen = AlmacenEnDisco(tmp_path)
    ruta, _ = _guardar(almacen, MP4)
    almacen.borrar(ruta)
    almacen.borrar(ruta)  # segunda vez: no hay nada que borrar y no es un error
    assert not almacen.existe(ruta)
    assert almacen.purgar_antes_de(datetime.now(UTC)) == 0
