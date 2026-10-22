"""Pruebas de contrato de RepositorioReportes (DT-01, paso 2).

Toda implementación del repositorio debe pasar exactamente las mismas pruebas: la de
memoria y la de PostgreSQL (paso 3), que usa la base de pruebas de tests/conftest.py.
"""
import threading
from copy import deepcopy
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.avisos.modelos import AvisoNuevo, EstadoAviso
from app.avisos.repositorio_postgres import RepositorioAvisosPostgres
from app.dominio.modelos import DecisionTriaje, EstadoReporte, Prioridad, Reporte, Ubicacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioEnMemoria()


def reporte_completo(codigo="ABCD1234"):
    return Reporte(
        codigo=codigo,
        descripcion="Perro atropellado frente al parque, no se puede parar",
        ubicacion=Ubicacion(latitud=7.8939, longitud=-72.5078, direccion="Av. 0 # 10-20"),
        video_segundos=45,
        estado=EstadoReporte.CLASIFICADO,
        prioridad=Prioridad.CRITICA,
        confianza=0.8,
        evidencias=["señal 'atropellad' -> critica", "señal 'no se puede parar' -> alta"],
        creado_en=datetime(2026, 10, 14, 15, 30, 12, 123456, tzinfo=UTC),
    )


def test_guardar_y_buscar_conserva_todos_los_campos(repositorio):
    esperado = reporte_completo()
    repositorio.guardar(deepcopy(esperado))
    assert repositorio.buscar("ABCD1234") == esperado


def test_conserva_campos_vacios(repositorio):
    """Reporte recién recibido: sin GPS, sin video, sin prioridad ni evidencias."""
    esperado = Reporte(codigo="SINGPS01", descripcion="Gato con sarna en el andén del barrio",
                       ubicacion=Ubicacion(direccion="Calle 10 # 5-30"),
                       creado_en=datetime(2026, 10, 14, 9, 0, tzinfo=UTC))
    repositorio.guardar(deepcopy(esperado))
    assert repositorio.buscar("SINGPS01") == esperado


def test_buscar_codigo_inexistente_devuelve_none(repositorio):
    assert repositorio.buscar("NOEXISTE") is None


def test_repositorio_nuevo_esta_vacio(repositorio):
    assert repositorio.todos() == []


def test_todos_devuelve_cada_reporte_guardado(repositorio):
    for codigo in ("AAAA0001", "BBBB0002", "CCCC0003"):
        repositorio.guardar(reporte_completo(codigo))
    assert sorted(r.codigo for r in repositorio.todos()) == ["AAAA0001", "BBBB0002", "CCCC0003"]


def test_guardar_el_mismo_codigo_actualiza_sin_duplicar(repositorio):
    """El veterinario confirma la prioridad: el reporte se vuelve a guardar con otro estado."""
    reporte = reporte_completo()
    repositorio.guardar(deepcopy(reporte))
    reporte.estado = EstadoReporte.CONFIRMADO
    reporte.prioridad = Prioridad.ALTA
    repositorio.guardar(deepcopy(reporte))
    assert len(repositorio.todos()) == 1
    guardado = repositorio.buscar("ABCD1234")
    assert (guardado.estado, guardado.prioridad) == (EstadoReporte.CONFIRMADO, Prioridad.ALTA)

# --- HU-02: confirmación con bitácora (RN-06, RN-16) ---------------------

def decision(codigo="ABCD1234", final=Prioridad.ALTA, justificacion="Camina con dificultad"):
    return DecisionTriaje(codigo=codigo, veterinario="vet@patitas.co",
                          prioridad_sugerida=Prioridad.CRITICA, prioridad_final=final,
                          justificacion=justificacion,
                          decidido_en=datetime(2026, 10, 15, 8, 30, tzinfo=UTC))


def test_confirmar_cambia_estado_y_prioridad_y_guarda_la_decision(repositorio):
    repositorio.guardar(reporte_completo())
    assert repositorio.confirmar(decision()) is True
    guardado = repositorio.buscar("ABCD1234")
    assert (guardado.estado, guardado.prioridad) == (EstadoReporte.CONFIRMADO, Prioridad.ALTA)
    assert repositorio.decisiones("ABCD1234") == [decision()]


def test_confirmar_un_reporte_ya_confirmado_devuelve_false_y_no_cambia_nada(repositorio):
    repositorio.guardar(reporte_completo())
    repositorio.confirmar(decision())
    assert repositorio.confirmar(decision(final=Prioridad.BAJA)) is False
    assert repositorio.buscar("ABCD1234").prioridad == Prioridad.ALTA
    assert len(repositorio.decisiones("ABCD1234")) == 1


def test_decisiones_de_un_reporte_sin_confirmar_es_lista_vacia(repositorio):
    repositorio.guardar(reporte_completo())
    assert repositorio.decisiones("ABCD1234") == []


def test_dos_veterinarios_a_la_vez_solo_uno_confirma(repositorio):
    repositorio.guardar(reporte_completo())
    salida = threading.Barrier(2)
    resultados = []

    def confirmar(final):
        salida.wait()
        resultados.append(repositorio.confirmar(decision(final=final)))

    hilos = [threading.Thread(target=confirmar, args=(p,)) for p in (Prioridad.ALTA,
                                                                      Prioridad.MEDIA)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(resultados) == [False, True]
    assert len(repositorio.decisiones("ABCD1234")) == 1


# --- RF-12 (#61): reenvío sin duplicados con clave de idempotencia ---------------------

CLAVE_PWA = "reenvio-de-la-pwa-0001"


def test_guardar_con_clave_nueva_guarda_el_reporte(repositorio):
    guardado = repositorio.guardar_con_clave(reporte_completo(), CLAVE_PWA)
    assert guardado == reporte_completo()
    assert repositorio.buscar("ABCD1234") == reporte_completo()
    assert repositorio.buscar_por_clave(CLAVE_PWA) == reporte_completo()


def test_guardar_con_clave_repetida_devuelve_el_primero_sin_duplicar(repositorio):
    """La PWA reenvía el mismo reporte al volver la señal: no se crea otro."""
    repositorio.guardar_con_clave(reporte_completo("PRIMERO1"), CLAVE_PWA)
    devuelto = repositorio.guardar_con_clave(reporte_completo("SEGUNDO2"), CLAVE_PWA)
    assert devuelto.codigo == "PRIMERO1"
    assert [r.codigo for r in repositorio.todos()] == ["PRIMERO1"]


def test_buscar_por_clave_inexistente_devuelve_none(repositorio):
    assert repositorio.buscar_por_clave(CLAVE_PWA) is None


def test_volver_a_guardar_el_reporte_conserva_su_clave(repositorio):
    """La confirmación del veterinario no borra la clave: un reenvío tardío no duplica."""
    repositorio.guardar_con_clave(reporte_completo(), CLAVE_PWA)
    repositorio.guardar(reporte_completo())
    assert repositorio.buscar_por_clave(CLAVE_PWA).codigo == "ABCD1234"


def test_dos_reenvios_a_la_vez_guardan_un_solo_reporte(repositorio):
    salida = threading.Barrier(2)
    codigos = []

    def reenviar(codigo):
        salida.wait()
        codigos.append(repositorio.guardar_con_clave(reporte_completo(codigo), CLAVE_PWA).codigo)

    hilos = [threading.Thread(target=reenviar, args=(c,)) for c in ("HILO0001", "HILO0002")]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert len(repositorio.todos()) == 1
    assert codigos[0] == codigos[1] == repositorio.todos()[0].codigo


# --- #63 (outbox): la confirmación y sus avisos se guardan juntos ------------------------

def avisos_de(repositorio, codigo="ABCD1234"):
    if isinstance(repositorio, RepositorioPostgres):
        return RepositorioAvisosPostgres(repositorio._motor).de_reporte(codigo)
    return repositorio.avisos.de_reporte(codigo)


AVISOS = [AvisoNuevo("ana@rescate.co", "Rescate alto ABCD1234"),
          AvisoNuevo("luis@rescate.co", "Rescate alto ABCD1234")]


def test_confirmar_guarda_los_avisos_pendientes_en_la_misma_operacion(repositorio):
    repositorio.guardar(reporte_completo())
    assert repositorio.confirmar(decision(), AVISOS) is True
    assert [(a.destinatario, a.estado) for a in avisos_de(repositorio)] == [
        ("ana@rescate.co", EstadoAviso.PENDIENTE), ("luis@rescate.co", EstadoAviso.PENDIENTE)]


def test_si_ya_estaba_confirmado_no_se_agregan_avisos(repositorio):
    repositorio.guardar(reporte_completo())
    repositorio.confirmar(decision())
    assert repositorio.confirmar(decision(), AVISOS) is False
    assert avisos_de(repositorio) == []


@pytest.mark.postgres
def test_si_falla_guardar_un_aviso_la_confirmacion_se_deshace(bd_limpia):
    """Punto de interrupción antes de confirmar la transacción: no queda nada a medias."""
    repositorio = RepositorioPostgres(bd_limpia)
    repositorio.guardar(reporte_completo())
    with pytest.raises(IntegrityError):
        repositorio.confirmar(decision(), [AvisoNuevo("ana@rescate.co", None)])  # NOT NULL
    assert repositorio.buscar("ABCD1234").estado == EstadoReporte.CLASIFICADO
    assert repositorio.decisiones("ABCD1234") == [] and avisos_de(repositorio) == []
