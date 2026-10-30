"""Afina un Transformer pequeño para el triaje y lo exporta a ONNX int8 (fase 7, RF-02, RNF-03).

Corre en GitHub Actions (.github/workflows/entrenar-triaje.yml), no en la PC ni en Render: usa
torch y transformers, que la API no instala. Pasos:

1. Datos sintéticos v2 (scripts/ia/datos_triaje.py): entrenamiento y validación.
2. Modelo base: mALBERT base cased 32k (cservan/multilingual-albert-base-cased-32k, Apache-2.0,
   ~12 M de parámetros porque ALBERT comparte las capas). Se le agrega una capa de 4 salidas
   (crítica, alta, media, baja) y se afina toda la red unas pocas épocas.
3. Exportar a ONNX y cuantizar a int8 (pesos de 32 bits → 8 bits: ~4 veces menos espacio).
4. Con el modelo int8 (el que se despliega) bajar el umbral de «crítica» hasta que el recall en
   validación llegue a 0,97 (margen sobre RNF-03: 0,95), como en el TF-IDF.

Uso:  python scripts/ia/entrenar_transformer.py --salida salida/onnx
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import torch  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from app.dominio.modelos import Prioridad  # noqa: E402
from app.triaje.modelo_onnx import METADATOS, ModeloOnnx  # noqa: E402
from app.triaje.normalizacion import normalizar  # noqa: E402
from scripts.ia.datos_triaje import conjuntos  # noqa: E402

BASE = "cservan/multilingual-albert-base-cased-32k"
REVISION = "d3f3c1addfec3420d3f306f674ed2087b34e0411"  # versión fija del modelo base
VERSION = "malbert-onnx-v1"
CLASES = ["alta", "baja", "critica", "media"]
MAX_TOKENS = 64
RECALL_OBJETIVO = 0.97


def lotes(textos, etiquetas, tamano, rng=None):
    indices = list(range(len(textos)))
    if rng:
        rng.shuffle(indices)
    for i in range(0, len(indices), tamano):
        parte = indices[i:i + tamano]
        yield [textos[j] for j in parte], torch.tensor([etiquetas[j] for j in parte])


def afinar(modelo, tokenizador, textos, etiquetas, epocas, tasa, semilla):
    rng = random.Random(semilla)
    pasos = epocas * ((len(textos) + 31) // 32)
    optimizador = torch.optim.AdamW(modelo.parameters(), lr=tasa, weight_decay=0.01)
    programa = get_linear_schedule_with_warmup(optimizador, int(pasos * 0.1), pasos)
    modelo.train()
    inicio = time.perf_counter()
    for epoca in range(epocas):
        total = 0.0
        for paso, (lote, y) in enumerate(lotes(textos, etiquetas, 32, rng)):
            x = tokenizador(lote, truncation=True, max_length=MAX_TOKENS, padding=True,
                            return_tensors="pt")
            perdida = modelo(**x, labels=y).loss
            perdida.backward()
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            optimizador.step()
            programa.step()
            optimizador.zero_grad()
            total += perdida.item()
            if paso % 20 == 0:
                print(f"época {epoca + 1} paso {paso}: pérdida {perdida.item():.4f} "
                      f"({time.perf_counter() - inicio:.0f} s)", flush=True)
        print(f"época {epoca + 1}: pérdida media {total / (paso + 1):.4f}", flush=True)
    modelo.eval()


def exportar(modelo, tokenizador, salida: Path) -> Path:
    ejemplo = tokenizador(["un perro atropellado"], return_tensors="pt")
    nombres = ["input_ids", "attention_mask", "token_type_ids"]
    ejes = {n: {0: "lote", 1: "piezas"} for n in nombres}
    completo = salida / "modelo_fp32.onnx"
    modelo.config.return_dict = False
    for dynamo in (False, True):  # exportador clásico; si la versión de torch ya no lo trae, dynamo
        try:
            torch.onnx.export(modelo, tuple(ejemplo[n] for n in nombres), str(completo),
                              input_names=nombres, output_names=["logits"],
                              dynamic_axes={**ejes, "logits": {0: "lote"}}, opset_version=17,
                              dynamo=dynamo)
            break
        except Exception as error:  # noqa: BLE001
            print(f"exportar con dynamo={dynamo} falló: {error}", flush=True)
    # Se importa después de entrenar: onnxruntime y torch traen cada uno su OpenMP.
    from onnxruntime.quantization import QuantType, quantize_dynamic

    cuantizado = salida / "modelo_int8.onnx"
    quantize_dynamic(str(completo), str(cuantizado), weight_type=QuantType.QInt8)
    print(f"ONNX fp32: {completo.stat().st_size / 1e6:.1f} MB; "
          f"int8: {cuantizado.stat().st_size / 1e6:.1f} MB")
    for sobrante in salida.glob("modelo_fp32.onnx*"):
        sobrante.unlink()
    return cuantizado


def umbral_critica(modelo: ModeloOnnx, validacion) -> float:
    criticos = [t for t, e, _ in validacion if e == "critica"]
    p_critica = [modelo.probabilidades(t)[Prioridad.CRITICA] for t in criticos]
    umbral = 0.5
    while umbral > 0.05 and sum(p >= umbral for p in p_critica) / len(p_critica) < RECALL_OBJETIVO:
        umbral = round(umbral - 0.05, 2)
    return umbral


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", type=Path, default=Path("salida/onnx"))
    parser.add_argument("--epocas", type=int, default=3)
    parser.add_argument("--tasa", type=float, default=5e-5)
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--muestras", type=int, default=0,
                        help="usar solo N reportes de entrenamiento (prueba rápida del flujo)")
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(args.semilla)
    torch.set_num_threads(os.cpu_count() or 1)
    print(f"hilos de torch: {torch.get_num_threads()}", flush=True)
    datos = conjuntos()
    if args.muestras:
        datos["entrenamiento"] = datos["entrenamiento"][:args.muestras]
    tokenizador = AutoTokenizer.from_pretrained(BASE, revision=REVISION)
    modelo = AutoModelForSequenceClassification.from_pretrained(
        BASE, revision=REVISION, num_labels=len(CLASES),
        id2label=dict(enumerate(CLASES)), label2id={c: i for i, c in enumerate(CLASES)})
    print(f"tokenizador: {type(tokenizador).__name__}", flush=True)
    textos = [normalizar(t) for t, _, _ in datos["entrenamiento"]]
    largos = sorted(len(ids) for ids in tokenizador(textos)["input_ids"])
    print(f"piezas por reporte: mediana {largos[len(largos) // 2]}, "
          f"p99 {largos[int(len(largos) * 0.99)]}, máx {largos[-1]}")
    afinar(modelo, tokenizador, textos, [CLASES.index(e) for _, e, _ in datos["entrenamiento"]],
           args.epocas, args.tasa, args.semilla)
    archivo = exportar(modelo, tokenizador, args.salida)
    tokenizador.backend_tokenizer.save(str(args.salida / "tokenizer.json"))
    metadatos = {
        "version": VERSION, "clases": CLASES, "max_tokens": MAX_TOKENS, "umbral_critica": 0.5,
        "archivo": archivo.name, "tokenizador": "tokenizer.json",
        "modelo_base": f"{BASE}@{REVISION}",
        "licencia": "Apache-2.0 (modelo base mALBERT, Servan et al. 2024, arXiv:2403.18338)",
        "datos": "sintéticos v2: scripts/ia/datos_triaje.py (6.000 de entrenamiento)",
        "afinado": {"epocas": args.epocas, "tasa": args.tasa, "semilla": args.semilla},
    }
    (args.salida / METADATOS).write_text(json.dumps(metadatos, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    metadatos["umbral_critica"] = umbral_critica(
        ModeloOnnx.desde_directorio(args.salida, hilos=0), datos["validacion"])
    print(f"Umbral de crítica: {metadatos['umbral_critica']}")
    (args.salida / METADATOS).write_text(json.dumps(metadatos, ensure_ascii=False, indent=1),
                                         encoding="utf-8")


if __name__ == "__main__":
    main()
