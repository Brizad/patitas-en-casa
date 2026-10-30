"""Adaptador ONNX del Transformer y reglas de seguridad con él (fase 7, RN-02, RN-03, RNF-03).

Estas pruebas usan dobles de la sesión de onnxruntime y del tokenizador: corren sin el modelo
ni onnxruntime. Las del modelo real están en test_triaje_transformer.py.
"""
import time
from types import SimpleNamespace

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion
from app.triaje import modelo_onnx
from app.triaje.combinado import clasificador_combinado, triaje_por_defecto
from app.triaje.modelo_onnx import ModeloOnnx
from app.triaje.servicio import ServicioTriaje

METADATOS = {"version": "prueba-onnx-v0", "clases": ["alta", "baja", "critica", "media"],
             "umbral_critica": 0.3, "max_tokens": 16}


class Tokenizador:
    def __init__(self):
        self.textos, self.maximo = [], None

    def enable_truncation(self, max_length):
        self.maximo = max_length

    def no_padding(self):
        pass

    def encode(self, texto):
        self.textos.append(texto)
        n = len(texto.split()) + 2
        return SimpleNamespace(ids=list(range(n)), attention_mask=[1] * n, type_ids=[0] * n)


class Sesion:
    """Devuelve siempre los mismos logits (orden de METADATOS["clases"])."""

    def __init__(self, logits, demora_s=0.0, falla=False):
        self.logits, self.demora_s, self.falla, self.recibido = logits, demora_s, falla, None

    def get_inputs(self):
        return [SimpleNamespace(name="input_ids"), SimpleNamespace(name="attention_mask")]

    def run(self, _salidas, entradas):
        if self.falla:
            raise RuntimeError("sesión rota")
        time.sleep(self.demora_s)
        self.recibido = entradas
        return [[self.logits]]


def modelo(logits, **kwargs):
    return ModeloOnnx(METADATOS, Sesion(logits, **kwargs), Tokenizador())


def reporte(descripcion):
    return Reporte(codigo="ONNX0001", descripcion=descripcion,
                   ubicacion=Ubicacion(direccion="Calle 10"))


def test_normaliza_el_texto_y_solo_pasa_las_entradas_que_pide_la_red():
    m = modelo([0.0, 0.0, 0.0, 0.0])
    m.clasificar("Perro ATROPELLADO en la vía")
    assert m._tokenizador.textos == ["perro atropellado en la via"]
    assert m._tokenizador.maximo == 16
    assert set(m._sesion.recibido) == {"input_ids", "attention_mask"}
    assert m._sesion.recibido["input_ids"].shape == (1, 7)


def test_softmax_da_probabilidades_que_suman_uno():
    probs = modelo([2.0, 0.0, 1.0, -1.0]).probabilidades("texto de prueba suficiente")
    assert abs(sum(probs.values()) - 1) < 1e-9
    assert max(probs, key=probs.get) == Prioridad.ALTA


def test_umbral_bajo_de_critica_prefiere_critica_rnf03():
    """P(crítica) ≈ 0,33 no es la mayor, pero pasa el umbral de 0,3: se elige crítica."""
    r = modelo([1.0, -5.0, 0.8, -5.0]).clasificar("perro tirado en la calle")
    assert r.prioridad == Prioridad.CRITICA
    assert r.evidencias[0].startswith("Transformer: alta con probabilidad")


def test_el_transformer_no_baja_lo_que_las_reglas_ven_critico():
    baja = modelo([-5.0, 5.0, -5.0, -5.0])
    r = clasificador_combinado(baja)("Gato convulsionando en la calle 10, ayuda")
    assert r.prioridad == Prioridad.CRITICA and len(r.evidencias) >= 3


def test_el_transformer_puede_subir_la_prioridad():
    alta = modelo([5.0, -5.0, -5.0, -5.0])
    r = clasificador_combinado(alta)("Un perrito tiene la patica colgando en Atalaya")
    assert r.prioridad == Prioridad.ALTA and r.confianza > 0.9


def test_rn02_media_con_poca_confianza_va_a_revision():
    media_dudosa = modelo([0.0, 0.0, -9.0, 0.4])  # media ≈ 0,43
    servicio = ServicioTriaje(clasificador_combinado(media_dudosa), version="v")
    evaluado = servicio.evaluar(reporte("Un gatico está achicopalado y no prueba bocado"))
    assert evaluado.prioridad == Prioridad.MEDIA
    assert evaluado.estado == EstadoReporte.REQUIERE_REVISION


def test_rn03_si_el_transformer_falla_hay_falla_segura():
    roto = modelo([0.0] * 4, falla=True)
    evaluado = ServicioTriaje(clasificador_combinado(roto), version="v").evaluar(
        reporte("Un perro atropellado en la avenida 0, no se mueve"))
    assert (evaluado.prioridad, evaluado.estado) == (Prioridad.ALTA, EstadoReporte.SIN_CLASIFICAR)
    assert evaluado.version_modelo is None


def test_rn03_si_el_transformer_tarda_hay_falla_segura():
    lento = modelo([0.0] * 4, demora_s=0.5)
    servicio = ServicioTriaje(clasificador_combinado(lento), tiempo_max_s=0.05, version="v")
    evaluado = servicio.evaluar(reporte("Un perro con sarna en el barrio Motilones"))
    assert (evaluado.prioridad, evaluado.estado) == (Prioridad.ALTA, EstadoReporte.SIN_CLASIFICAR)


def test_sin_archivos_del_transformer_la_api_sigue_con_tfidf(monkeypatch, tmp_path):
    monkeypatch.delenv("PATITAS_TRIAJE_TRANSFORMER", raising=False)
    monkeypatch.setattr(modelo_onnx, "DIRECTORIO", tmp_path)
    assert triaje_por_defecto()[1] == "reglas-v0+tfidf-lr-v1"


def test_transformer_danado_no_tumba_la_api(monkeypatch, tmp_path):
    monkeypatch.delenv("PATITAS_TRIAJE_TRANSFORMER", raising=False)
    (tmp_path / modelo_onnx.METADATOS).write_text("{no es json", encoding="utf-8")
    monkeypatch.setattr(modelo_onnx, "DIRECTORIO", tmp_path)
    assert triaje_por_defecto()[1] == "reglas-v0+tfidf-lr-v1"


def test_con_el_transformer_la_version_lo_dice_salvo_que_se_apague(monkeypatch, tmp_path):
    monkeypatch.delenv("PATITAS_TRIAJE_TRANSFORMER", raising=False)
    (tmp_path / modelo_onnx.METADATOS).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(modelo_onnx, "DIRECTORIO", tmp_path)
    monkeypatch.setattr(modelo_onnx, "cargar_modelo_onnx", lambda _d: modelo([0.0] * 4))
    clasificador, version = triaje_por_defecto()
    assert version == "reglas-v0+prueba-onnx-v0"
    assert clasificador("Gato convulsionando en la calle 10").prioridad == Prioridad.CRITICA
    monkeypatch.setenv("PATITAS_TRIAJE_TRANSFORMER", "0")
    assert triaje_por_defecto()[1] == "reglas-v0+tfidf-lr-v1"
