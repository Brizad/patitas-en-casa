"""Validación del triaje con reportes reales (DT-04, RNF-03). Aquí NO hay datos reales: los
CSV de estas pruebas salen del generador sintético y solo comprueban que el script mide,
parte y decide bien. La validación de verdad la hace Brayan con reportes confirmados."""
import json

import pytest

from app.dominio.modelos import Prioridad
from app.triaje.clasificador import Resultado
from app.triaje.modelo import ARCHIVO
from scripts.ia.generar_datos_sinteticos import generar
from scripts.ia.validar_con_reales import (
    MIN_CRITICAS,
    DatosInvalidos,
    leer,
    main,
    medir,
    partir,
    recomendar,
    veredicto,
    wilson,
)


def csv_de(tmp_path, filas, encabezado="descripcion,prioridad"):
    ruta = tmp_path / "datos_reales_triaje.csv"
    ruta.write_text(encabezado + "\n" + "\n".join(f'"{t}",{p}' for t, p in filas), "utf-8")
    return ruta


def medida(halladas, criticas, aciertos=None, total=None):
    return {"criticas": criticas, "halladas": halladas, "intervalo": wilson(halladas, criticas),
            "recall_critica": halladas / criticas if criticas else None,
            "aciertos": aciertos if aciertos is not None else halladas,
            "total": total or criticas}


def test_lee_el_csv_y_los_textos_repetidos_cuentan_una_vez(tmp_path):
    ruta = csv_de(tmp_path, [("Perro atropellado que no respira", "critica"),
                             ("Perro atropellado que no respira", " CRITICA "),
                             ("Gato con sarna en el lomo", "baja")])
    assert leer(ruta) == [("Perro atropellado que no respira", Prioridad.CRITICA),
                          ("Gato con sarna en el lomo", Prioridad.BAJA)]


@pytest.mark.parametrize(("filas", "encabezado", "error"), [
    ([("Perro herido", "urgente")], "descripcion,prioridad", "Fila 2: prioridad «urgente»"),
    ([("", "alta")], "descripcion,prioridad", "Fila 2: la descripción está vacía"),
    ([("Perro que cojea", "media"), ("Perro que cojea", "alta")], "descripcion,prioridad",
     "Fila 3: el mismo texto aparece con dos prioridades"),
    ([("Perro herido", "alta")], "texto,etiqueta", "columnas «descripcion» y «prioridad»"),
])
def test_un_csv_malo_se_rechaza_diciendo_la_fila(tmp_path, filas, encabezado, error):
    with pytest.raises(DatosInvalidos, match=error):
        leer(csv_de(tmp_path, filas, encabezado))


def test_el_intervalo_de_wilson_es_ancho_con_pocos_casos():
    bajo, alto = wilson(30, 30)
    assert bajo == pytest.approx(0.886, abs=0.002) and alto == 1.0
    assert wilson(100, 100)[0] > 0.95 and wilson(0, 0) == (0.0, 1.0)
    bajo, alto = wilson(19, 25)  # el 0,76 de los casos escritos: entre 0,57 y 0,89
    assert bajo == pytest.approx(0.566, abs=0.003) and alto == pytest.approx(0.885, abs=0.003)


def test_con_pocas_criticas_no_se_afirma_nada_aunque_el_recall_sea_perfecto():
    assert MIN_CRITICAS == 30
    assert veredicto(medida(29, 29)).startswith("AÚN NO SE PUEDE SABER")


def test_el_veredicto_de_rnf03_distingue_no_cumple_muestra_y_cumple():
    assert veredicto(medida(27, 30)).startswith("NO CUMPLE RNF-03")
    assert veredicto(medida(30, 30)).startswith("CUMPLE RNF-03 EN ESTA MUESTRA")
    assert veredicto(medida(100, 100)).startswith("CUMPLE RNF-03 (")


def test_la_prueba_se_aparta_por_prioridad_y_no_se_mezcla_con_el_entrenamiento():
    casos = [(texto, Prioridad(etiqueta)) for texto, etiqueta in dict(generar(400, 3)).items()]
    entrenamiento, prueba = partir(casos)
    assert not set(entrenamiento) & set(prueba)
    assert len(entrenamiento) + len(prueba) == len(casos)
    por_clase = [sum(p == prioridad for _, p in prueba) for prioridad in Prioridad]
    assert max(por_clase) - min(por_clase) <= 3 and min(por_clase) > 0
    assert partir(casos) == (entrenamiento, prueba)  # misma semilla, misma partición


def test_solo_se_recomienda_un_candidato_que_cumple_y_no_pierde_criticas():
    actual = medida(38, 40, aciertos=90, total=120)
    assert recomendar(actual, medida(40, 40, 100, 120)).startswith("CANDIDATO MEJOR")
    assert "menos críticas" in recomendar(medida(40, 40, 90, 120), medida(39, 40, 110, 120))
    assert "no cumple RNF-03" in recomendar(medida(32, 40, 90, 120), medida(36, 40, 100, 120))
    assert "no acierta más" in recomendar(actual, medida(38, 40, 90, 120))
    assert "muy pocas críticas" in recomendar(actual, medida(10, 10, 30, 30))


def test_el_comando_mide_el_clasificador_actual_y_da_su_veredicto(tmp_path, capsys):
    filas = list(dict(generar(160, 11)).items())
    assert main([str(csv_de(tmp_path, filas))]) == 0
    salida = capsys.readouterr().out
    assert "reglas-v0+tfidf-lr-v1" in salida and "| Real \\ Sugerida |" in salida
    assert "RNF-03" in salida
    assert main([str(csv_de(tmp_path, [("x", "nada")]))]) == 2


def test_medir_cuenta_las_criticas_que_quedaron_abajo():
    m = medir(lambda _texto: Resultado(Prioridad.BAJA, 0.9, []),
              [("a", Prioridad.CRITICA), ("b", Prioridad.BAJA)])
    assert (m["halladas"], m["criticas_como_media_o_baja"], m["aciertos"]) == (0, 1, 1)


def test_reentrenar_escribe_un_candidato_y_nunca_toca_el_modelo_publicado(tmp_path, capsys):
    pytest.importorskip("sklearn")
    publicado = ARCHIVO.read_bytes()
    filas = list(dict(generar(240, 5)).items())
    salida = tmp_path / "candidato.json"
    assert main([str(csv_de(tmp_path, filas)), "--reentrenar", "--salida", str(salida)]) == 0
    assert ARCHIVO.read_bytes() == publicado
    candidato = json.loads(salida.read_text("utf-8"))
    assert candidato["version"] == "tfidf-lr-candidato" and "reales" in candidato["datos"]
    texto = capsys.readouterr().out
    assert "Prueba real apartada" in texto and "en la misma prueba real" in texto
