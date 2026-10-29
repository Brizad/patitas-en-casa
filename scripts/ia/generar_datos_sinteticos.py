"""Genera reportes de emergencia SINTÉTICOS y etiquetados para entrenar el triaje (fase 4, #95).

¿Por qué sintéticos? Para entrenar con datos reales hacen falta unos 1.000 reportes
etiquetados por veterinarios (SUP-05) y todavía no existen. Estos datos los arma un programa
con plantillas: sirven para construir y probar el sistema completo (entrenar, medir,
desplegar), NO para afirmar que el modelo acierta con reportes reales. Cuando haya reportes
confirmados (la prioridad final que guarda la bitácora, RF-20, es la etiqueta), se reentrena
con ellos usando el mismo script de entrenamiento.

Cada reporte combina una situación principal (que define la etiqueta), a veces una situación
secundaria menos grave, y ruido: animal, lugar de Cúcuta, frases de relleno y negaciones
(«no sangra») que obligan al modelo a no fiarse de una sola palabra.

Uso:  python scripts/ia/generar_datos_sinteticos.py --cantidad 4000 --salida datos.csv
"""
from __future__ import annotations

import argparse
import csv
import random

SITUACIONES = {
    "critica": [
        "fue atropellado y no se mueve", "está convulsionando", "no respira bien",
        "está inconsciente", "tiene una hemorragia muy fuerte", "echa espuma por la boca, "
        "parece envenenado", "sangra muchísimo por la cabeza", "lo arrolló una moto y no "
        "reacciona", "está tirado sin reaccionar", "se está ahogando", "tiene una herida muy "
        "grande y pierde mucha sangre", "le dieron veneno y tiembla",
    ],
    "alta": [
        "tiene una fractura en la pata", "tiene una herida abierta en el lomo",
        "sangra un poco de la oreja", "no se puede parar", "tiene la pata hinchada y no la "
        "apoya", "tiene un corte profundo", "lo mordió otro perro y tiene heridas",
        "tiene un anzuelo en la boca", "tiene quemaduras en el lomo", "lo golpearon y cojea "
        "mucho", "tiene un ojo lastimado y sangra", "quedó atrapado y se lastimó la pata",
    ],
    "media": [
        "está vomitando", "no come hace días", "está muy flaco y desnutrido",
        "cojea un poco", "tiene diarrea", "tiene los ojos con pus", "tose mucho",
        "está deshidratado", "tiene la panza muy hinchada", "tiene fiebre y está decaído",
        "tiene una infección en la piel", "tiene un tumor pequeño",
    ],
    "baja": [
        "tiene sarna", "tiene garrapatas", "está abandonado pero se ve sano",
        "tiene pulgas", "anda solo por el barrio", "está sucio y con el pelo enredado",
        "una perrita con cachorros sanos busca hogar", "lleva días en la calle pero come",
        "lo dejaron amarrado sin agua", "está asustado debajo de un carro",
        "tiene las uñas muy largas", "necesita un hogar",
    ],
}
# Negaciones: la palabra grave aparece, pero niega el problema (casos difíciles).
NEGACIONES = ["no está sangrando", "no tiene heridas", "no convulsiona", "no parece "
              "atropellado", "no tiene fracturas", "no está inconsciente"]
ANIMALES = ["un perro", "una perrita", "un gato", "un gatito negro", "un cachorro",
            "una gata", "un perro criollo", "un perro grande", "una gatica blanca"]
LUGARES = ["en la avenida 0", "frente al parque Santander", "en el barrio La Libertad",
           "cerca del Malecón", "en la comuna 6", "en Atalaya", "por el Terminal",
           "en la calle 10", "en el barrio Motilones", "detrás del colegio", ""]
INICIOS = ["", "Hola, ", "Buenas, ", "Por favor ayuda, ", "Urgente: ", "Reporto que "]
EXTRAS = ["", "", "Por favor vengan.", "Lleva ahí desde la mañana.", "Nadie lo recoge.",
          "Es urgente.", "Gracias.", "Mandé foto al grupo del barrio.", "Está muy triste."]
ORDEN = ["critica", "alta", "media", "baja"]


def reporte(rng: random.Random, etiqueta: str) -> str:
    partes = [rng.choice(SITUACIONES[etiqueta])]
    menos_graves = ORDEN[ORDEN.index(etiqueta) + 1:]
    if menos_graves and rng.random() < 0.35:  # una situación secundaria menos grave
        partes.append(rng.choice(SITUACIONES[rng.choice(menos_graves)]))
    if etiqueta in ("media", "baja") and rng.random() < 0.3:
        partes.insert(0, rng.choice(NEGACIONES))  # negación: no sube la gravedad
    rng.shuffle(partes)
    texto = (f"{rng.choice(INICIOS)}{rng.choice(ANIMALES)} {rng.choice(LUGARES)} "
             f"{' y '.join(partes)}. {rng.choice(EXTRAS)}")
    return " ".join(texto.split())


def generar(cantidad: int, semilla: int = 42) -> list[tuple[str, str]]:
    """Balanceado: la misma cantidad por prioridad. Con la misma semilla, los mismos datos."""
    rng = random.Random(semilla)
    return [(reporte(rng, ORDEN[i % 4]), ORDEN[i % 4]) for i in range(cantidad)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cantidad", type=int, default=4000)
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--salida", default="datos_sinteticos_triaje.csv")
    args = parser.parse_args()
    with open(args.salida, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["texto", "prioridad"])
        escritor.writerows(generar(args.cantidad, args.semilla))
    print(f"{args.cantidad} reportes sintéticos en {args.salida}")


if __name__ == "__main__":
    main()
