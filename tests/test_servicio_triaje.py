import time
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.triaje.clasificador import Resultado
from app.triaje.servicio import ServicioTriaje, ordenar_cola


def nuevo_reporte(texto="perro herido en la calle 10", minutos=0):
    r = Reporte(codigo="ABCD1234", descripcion=texto, ubicacion=Ubicacion(direccion="Calle 10"))
    r.creado_en = datetime(2026, 9, 29, 10, 0, tzinfo=UTC) + timedelta(minutes=minutos)
    return r


def stub(prioridad, confianza):
    """Stub: devuelve una respuesta fija, sin lógica."""
    return lambda _texto: Resultado(prioridad, confianza, ["stub"])


def test_confianza_baja_exige_revision_y_no_queda_baja_automatica():
    servicio = ServicioTriaje(clasificador=stub(Prioridad.BAJA, 0.45))
    r = servicio.evaluar(nuevo_reporte())
    assert r.estado == EstadoReporte.REQUIERE_REVISION


def test_confianza_alta_queda_clasificado():
    servicio = ServicioTriaje(clasificador=stub(Prioridad.CRITICA, 0.8))
    r = servicio.evaluar(nuevo_reporte())
    assert r.estado == EstadoReporte.CLASIFICADO
    assert r.prioridad == Prioridad.CRITICA


def test_falla_del_clasificador_aplica_falla_segura():
    clasificador_roto = Mock(side_effect=RuntimeError("modelo caído"))
    r = ServicioTriaje(clasificador=clasificador_roto).evaluar(nuevo_reporte("perro herido"))
    clasificador_roto.assert_called_once_with("perro herido")
    assert r.estado == EstadoReporte.SIN_CLASIFICAR
    assert r.prioridad == Prioridad.ALTA


def test_cola_ubica_revision_sobre_media_y_critico_primero():
    media = nuevo_reporte(minutos=0)
    media.prioridad, media.estado = Prioridad.MEDIA, EstadoReporte.CLASIFICADO
    revision = nuevo_reporte(minutos=1)
    revision.prioridad, revision.estado = Prioridad.BAJA, EstadoReporte.REQUIERE_REVISION
    critica = nuevo_reporte(minutos=5)
    critica.prioridad, critica.estado = Prioridad.CRITICA, EstadoReporte.CLASIFICADO
    assert ordenar_cola([media, revision, critica]) == [critica, revision, media]


def test_confianza_baja_con_prioridad_critica_no_se_degrada():
    """Camino 4 de V(G)=4: la baja confianza solo exige revisión en prioridades media o baja."""
    servicio = ServicioTriaje(clasificador=stub(Prioridad.CRITICA, 0.5))
    r = servicio.evaluar(nuevo_reporte("perro convulsionando"))
    assert r.estado == EstadoReporte.CLASIFICADO
    assert r.prioridad == Prioridad.CRITICA


def clasificador_colgado(segundos):
    """Simula un modelo que no responde a tiempo."""
    def clasificar_lento(_texto):
        time.sleep(segundos)
        return Resultado(Prioridad.BAJA, 0.9, ["tarde"])
    return clasificar_lento


def test_tiempo_agotado_aplica_falla_segura():
    """PA-02 / RN-03: si el clasificador no responde a tiempo, el reporte sube a alta."""
    servicio = ServicioTriaje(clasificador=clasificador_colgado(1.0), tiempo_max_s=0.1)
    r = servicio.evaluar(nuevo_reporte())
    assert r.estado == EstadoReporte.SIN_CLASIFICAR
    assert r.prioridad == Prioridad.ALTA


def test_bug03_clasificaciones_colgadas_no_bloquean_reportes_siguientes():
    """Regresión BUG-03 (#17): dos clasificaciones colgadas agotaban los dos hilos del pool."""
    def clasificador(texto):
        if "colgado" in texto:
            time.sleep(1.0)
        return Resultado(Prioridad.CRITICA, 0.8, ["señal crítica"])

    servicio = ServicioTriaje(clasificador=clasificador, tiempo_max_s=0.2)
    servicio.evaluar(nuevo_reporte("reporte colgado número uno"))
    servicio.evaluar(nuevo_reporte("reporte colgado número dos"))
    r = servicio.evaluar(nuevo_reporte("perro atropellado que no respira"))
    assert r.estado == EstadoReporte.CLASIFICADO
    assert r.prioridad == Prioridad.CRITICA
