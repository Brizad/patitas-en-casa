"""Pruebas que matan mutantes sobrevivientes de mutmut (#272, docs/tesis/pruebas.md).

Cada una cubre una regla que ninguna prueba vigilaba de verdad: si alguien cambia un «<» por
«<=», un «and» por «or» o quita una condición, ahora alguna prueba falla.
"""
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.adopciones.reglas import restricciones_duras
from app.cupos.fichas import MIN_LETRAS_NOTA, NotaInvalida, ServicioFichas
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import (
    Animal,
    DecisionTriaje,
    Especie,
    EstadoReporte,
    Prioridad,
    Refugio,
    Reporte,
    ResultadoRescate,
    Rol,
    TipoNota,
    Ubicacion,
    Usuario,
)
from app.reportes.repositorio import RepositorioEnMemoria
from app.rescates.repositorio import RepositorioRescatesEnMemoria
from app.rescates.servicio import PasoInvalido, ServicioRescates
from app.triaje.clasificador import Resultado
from app.triaje.video import fusionar
from tests.test_compatibilidad import PERFIL, animal

AHORA = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


# --- RN-05: restricciones duras de adopción ----------------------------------------------

def test_rn05_el_animal_que_necesita_patio_no_va_a_un_hogar_sin_patio():
    sin_patio = replace(PERFIL, tiene_patio=False)
    assert restricciones_duras(sin_patio, animal(necesita_patio=True)) == [
        "el animal necesita patio y el hogar no tiene"]
    assert restricciones_duras(PERFIL, animal(necesita_patio=True)) == []  # el hogar tiene


def test_rn05_otros_animales_dice_el_motivo_exacto():
    con_otros = replace(PERFIL, otros_animales=True)
    assert restricciones_duras(con_otros, animal(apto_otros_animales=False)) == [
        "el animal no convive con otros animales y en el hogar hay otros"]


# --- RN-07: fusión de texto y video -------------------------------------------------------

def test_rn07_con_la_misma_prioridad_manda_el_texto_y_no_hay_discrepancia():
    texto = Resultado(Prioridad.ALTA, 0.7, ["a"])
    r = fusionar(texto, Resultado(Prioridad.ALTA, 0.9, ["b"]))
    assert (r.prioridad, r.confianza, r.evidencias) == (Prioridad.ALTA, 0.7, ["a", "video: b"])


def test_rn07_si_el_texto_es_mas_grave_conserva_su_confianza_y_suma_las_evidencias():
    r = fusionar(Resultado(Prioridad.CRITICA, 0.8, ["a"]), Resultado(Prioridad.ALTA, 0.9, ["b"]))
    assert r.prioridad == Prioridad.CRITICA and r.confianza == 0.8
    assert r.evidencias[:2] == ["a", "video: b"] and "gana la más alta" in r.evidencias[2]


# --- Ficha clínica: límite de letras ------------------------------------------------------

def fichas():
    repo = RepositorioCuposEnMemoria(Refugio("R", capacidad=5))
    from app.cupos.servicio import ServicioCupos
    animal_ = Animal("Toby", Especie.PERRO, "Sano")
    ServicioCupos(repo, notificador=None).registrar_ingreso(animal_)
    return ServicioFichas(repo, reloj=lambda: AHORA), animal_.id


def test_la_nota_con_justo_el_minimo_de_letras_se_acepta_y_queda_con_su_hora():
    servicio, animal_id = fichas()
    vet = Usuario("vet@x.co", "Vet", Rol.VETERINARIO, "h")
    nota = servicio.agregar_nota(animal_id, vet, TipoNota.OBSERVACION, "a" * MIN_LETRAS_NOTA)
    assert nota.registrada_en == AHORA
    with pytest.raises(NotaInvalida) as error:
        servicio.agregar_nota(animal_id, vet, TipoNota.OBSERVACION, "a" * (MIN_LETRAS_NOTA - 1))
    assert str(error.value) == "Escribe la nota con palabras."
    coordinador = Usuario("co@x.co", "Co", Rol.COORDINADOR, "h")
    with pytest.raises(PermissionError) as error:
        servicio.agregar_nota(animal_id, coordinador, TipoNota.OBSERVACION, "Sano y activo")
    assert str(error.value) == "Solo el veterinario escribe en la ficha clínica."


# --- RN-08: rescates ----------------------------------------------------------------------

def rescates(*codigos, minutos_desde_confirmacion=60, minutos=None):
    """Reportes críticos confirmados hace «minutos_desde_confirmacion» (o lo que diga
    «minutos» para cada código)."""
    reportes = RepositorioEnMemoria()
    for codigo in codigos:
        reportes.guardar(Reporte(codigo=codigo, descripcion="Perro atropellado, no se mueve",
                                 ubicacion=Ubicacion(direccion="Calle 10"),
                                 estado=EstadoReporte.CLASIFICADO, prioridad=Prioridad.CRITICA,
                                 creado_en=AHORA))
        reportes.confirmar(DecisionTriaje(
            codigo, "vet@x.co", Prioridad.CRITICA, Prioridad.CRITICA,
            decidido_en=AHORA - timedelta(
                minutes=(minutos or {}).get(codigo, minutos_desde_confirmacion))))
    repo = RepositorioRescatesEnMemoria()
    return ServicioRescates(reportes, repo, reloj=lambda: AHORA), repo


def persona(correo):
    return Usuario(correo, correo, Rol.RESCATISTA, "h")


def test_otro_rescatista_no_cierra_un_rescate_ajeno_aunque_este_en_camino():
    servicio, _ = rescates("AAAA0001")
    ana, beto = persona("ana@x.co"), persona("beto@x.co")
    for r in (ana, beto):
        servicio.cambiar_disponibilidad(r, True)
    servicio.aceptar(ana, "AAAA0001")
    for quien, codigo, mensaje in ((beto, "AAAA0001", "No tienes ese rescate activo."),
                                   (ana, "AAAA0001", "Primero marca Llegué al sitio."),
                                   (ana, "NOEXISTE", "No tienes ese rescate activo.")):
        with pytest.raises(PasoInvalido) as error:
            servicio.registrar_resultado(quien, codigo, ResultadoRescate.TRASLADADO)
        assert str(error.value) == mensaje  # el texto exacto que ve el rescatista


def test_la_zona_puede_ser_las_10_comunas_y_no_una_comuna_11():
    servicio, repo = rescates()
    ana = persona("ana@x.co")
    servicio.cambiar_zona(ana, frozenset(range(1, 11)))
    assert repo.zona("ana@x.co") == frozenset(range(1, 11))
    with pytest.raises(ValueError, match="van de 1 a 10"):
        servicio.cambiar_zona(ana, frozenset({11}))


def test_rf23_un_caso_ya_tomado_no_frena_el_escalamiento_de_los_demas():
    servicio, repo = rescates("AAAA0001", "BBBB0002", "CCCC0003")
    ana = persona("ana@x.co")
    servicio.cambiar_disponibilidad(ana, True)
    servicio.aceptar(ana, "AAAA0001")  # el primero ya tiene rescatista
    assert sorted(servicio.escalar_vencidos()) == ["BBBB0002", "CCCC0003"]
    assert servicio.escalar_vencidos() == []  # una sola vez
    assert repo.escalados() == {"BBBB0002", "CCCC0003"}


def test_rf23_un_caso_que_aun_no_vence_no_frena_a_los_que_ya_vencieron():
    servicio, _ = rescates("AAAA0001", "BBBB0002", minutos={"AAAA0001": 5})  # 5 min: aún no
    assert servicio.escalar_vencidos() == ["BBBB0002"]


class OtroProcesoEscalo(RepositorioRescatesEnMemoria):
    """Simula que otro proceso marcó el primero justo antes (marcar_escalado → False)."""

    def marcar_escalado(self, codigo, momento):
        return False if codigo == "AAAA0001" else super().marcar_escalado(codigo, momento)


def test_rf23_si_otro_proceso_escalo_uno_los_demas_igual_se_escalan():
    servicio, _ = rescates("AAAA0001", "BBBB0002")
    servicio._rescates = OtroProcesoEscalo()
    assert servicio.escalar_vencidos() == ["BBBB0002"]
