"""Reportes SINTÉTICOS v2 para el triaje: más grandes y más parecidos a WhatsApp (fase 7).

Siguen siendo inventados (DT-04 abierta): sirven para comparar modelos, no prueban acierto real.

Qué cambia frente a generar_datos_sinteticos.py (v1):
- Jerga y forma de escribir de Cúcuta: parce, chandoso, gatico, «la moto lo levantó»,
  abreviaturas de WhatsApp (q, xq, porfa, ta), errores de ortografía, MAYÚSCULAS, sin tildes.
- Negaciones de algo más grave que la etiqueta («no sangra», «ya no cojea»).
- Tres conjuntos con semillas distintas: entrenamiento, validación y prueba. La prueba es
  fija (scripts/ia/datos/triaje_prueba.csv) e incluye casos difíciles que el modelo nunca vio:
  frases reservadas solo para la prueba, negaciones nuevas y ruido fuerte.

Uso:  python scripts/ia/datos_triaje.py --salida-dir scripts/ia/datos
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

ORDEN = ["critica", "alta", "media", "baja"]
# Frases comunes (entrenamiento, validación y prueba).
SITUACIONES = {
    "critica": [
        "fue atropellado y no se mueve", "la moto lo levantó y quedó tieso", "está convulsionando",
        "le está dando un ataque, tiembla y bota espuma", "no respira bien, se está ahogando",
        "está inconsciente", "está tirado sin reaccionar", "bota mucha sangre por la boca",
        "tiene una hemorragia muy fuerte", "lo envenenaron y bota espuma por la boca",
        "se comió veneno de ratas y está temblando", "está en las últimas, casi no respira",
        "lo arrolló una buseta y sangra un montón", "le dio un golpe de calor y está desmayado",
        "se está desangrando", "lo cogió un carro y no reacciona", "no respira",
        "está pariendo y un cachorro se quedó atascado hace horas", "lo apuñalaron y no se para",
    ],
    "alta": [
        "tiene una pata partida", "tiene la pata fracturada", "tiene una herida abierta en el lomo",
        "sangra un poquito de la oreja", "no se puede parar", "lo mordió otro perro y tiene huecos",
        "tiene un corte profundo", "tiene un anzuelo enterrado en la boca", "tiene quemaduras",
        "lo cascaron con un palo y cojea mucho", "tiene un ojo reventado",
        "quedó atrapado en una reja y se lastimó la pata", "tiene una herida con gusanos",
        "la moto lo levantó, camina pero arrastra las patas de atrás", "le echaron agua caliente",
        "tiene la pata hinchada y no la apoya", "le tiraron una piedra y tiene la cabeza rota",
    ],
    "media": [
        "está vomitando", "vomita todo lo que come", "no come hace días",
        "está en los puros huesos", "está muy flaco y desnutrido", "cojea un poco",
        "tiene diarrea", "tiene los ojos con pus", "tose mucho", "está deshidratado",
        "tiene la barriga muy hinchada", "está decaído con fiebre",
        "tiene una infección en la piel", "tiene una bolita en la panza", "estornuda y bota moco",
        "se rasca hasta sacarse sangre poquita", "tiene la oreja con mal olor",
    ],
    "baja": [
        "tiene sarna", "está lleno de garrapatas", "tiene pulgas",
        "está abandonado pero se ve sano",
        "anda solo por el barrio", "está sucio y con el pelo enredado", "necesita un hogar",
        "una perrita con cachorros sanos busca hogar", "lleva días en la calle pero come",
        "está asustado debajo de un carro", "tiene las uñas muy largas", "se perdió y tiene collar",
        "lo dejaron en una caja en la esquina", "está pelado de sarna pero come bien",
        "es mansito y busca quien lo adopte",
    ],
}
# Frases reservadas: solo en la prueba, para ver si el modelo entiende formas nuevas de decirlo.
SOLO_PRUEBA = {
    "critica": ["lo volteó un camión y está privado", "se desplomó y no vuelve en sí",
                "le sale sangre a chorros", "está morado y no coge aire",
                "quedó hecho nada en la vía y no se mueve",
                "tiene ataques seguidos y no despierta"],
    "alta": ["tiene la patica colgando", "le abrieron la cabeza de una pedrada pero está despierto",
             "trae un alambre enterrado en el cuello", "tiene una cortada fea que no cierra",
             "lo pisó una moto y no apoya la pata"],
    "media": ["está achicopalado y no prueba bocado", "tiene churrias",
              "se le notan las costillas", "anda renqueando un poquito",
              "está trasbocando desde ayer"],
    "baja": ["es un chandoso callejero muy juicioso que busca casa",
             "se le ve el cuero por la sarna",
             "anda vagando por la cuadra pidiendo comida", "lo botaron en el lote, está gordito"],
}
# Negación de una señal del nivel indicado: el texto la menciona, pero no sube la gravedad.
NEGACIONES = {
    "critica": ["no está inconsciente", "respira bien", "no lo atropellaron", "no convulsiona",
                "no está envenenado", "está despierto"],
    "alta": ["no sangra", "no tiene heridas", "no tiene nada roto", "sí se para", "camina normal"],
    "media": ["ya no cojea", "sí come", "no ha vomitado", "no está flaco"],
}
NEGACIONES_PRUEBA = {
    "critica": ["no está privado", "ya respira normal", "tampoco lo cogió un carro"],
    "alta": ["tampoco sangra", "no se ve herido", "ni un rasguño tiene"],
    "media": ["ni cojea ni nada", "está comiendo juicioso", "ya no tiene diarrea"],
}
ANIMALES = ["un perro", "una perrita", "un perrito", "un gato", "un gatico", "una gatica",
            "un michi", "un cachorro", "un chandoso", "un perro criollo", "un pitbull",
            "una gata", "un gatico negro", "un perro grande", "el perrito del barrio"]
LUGARES = ["en la avenida 0", "frente al parque Santander", "en el barrio La Libertad",
           "cerca del Malecón", "en la comuna 6", "en Atalaya", "por el Terminal",
           "en la calle 10", "en Motilones", "detrás del colegio", "en El Contento",
           "por la Diagonal Santander", "en Comuneros", "en La Ínsula", "en Prados del Este",
           "en la Libertadores", "por el Canal Bogotá", "en Juan Atalaya", "en Caobos",
           "por Ventura Plaza", "en San Luis", "en el anillo vial", ""]
INICIOS = ["", "Hola", "Buenas", "Buenas tardes", "Parce", "Ayuda porfa", "Urgente",
           "Vecinos", "Por favor", "Quiero reportar que", "Uy", "Qué pesar", "Ayudaaa"]
EXTRAS = ["", "", "Por favor vengan", "Lleva ahí desde la mañana", "Nadie lo recoge",
          "Es urgente", "Gracias", "Mandé foto al grupo", "Dios les pague", "El vecino lo vio",
          "Ayúdenme que no tengo carro", "🙏", "😢😢"]
# Abreviaturas de WhatsApp y cambios de ortografía frecuentes.
ABREVIATURAS = {"que": "q", "porque": "xq", "por": "x", "favor": "fa", "está": "ta",
                "también": "tb", "aquí": "aki", "de": "d", "muy": "mui", "porfa": "xfa",
                "hace": "ase", "hay": "ay", "vengan": "bengan"}
CAMBIOS = [("s", "z"), ("c", "s"), ("v", "b"), ("b", "v"), ("ll", "y"), ("h", ""), ("qu", "k")]
TILDES = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")


def _palabra_con_error(rng: random.Random, palabra: str) -> str:
    if len(palabra) < 4:
        return palabra
    i = rng.randrange(1, len(palabra) - 1)
    tipo = rng.randrange(4)
    if tipo == 0:  # letras cambiadas de lugar
        return palabra[:i] + palabra[i + 1] + palabra[i] + palabra[i + 2:]
    if tipo == 1:  # letra que falta
        return palabra[:i] + palabra[i + 1:]
    if tipo == 2:  # letra repetida
        return palabra[:i] + palabra[i] * 2 + palabra[i + 1:]
    viejo, nuevo = rng.choice(CAMBIOS)  # error de ortografía por sonido
    return palabra.replace(viejo, nuevo, 1)


def ensuciar(rng: random.Random, texto: str, fuerza: float) -> str:
    """Ruido de chat: abreviaturas, errores, sin tildes y mayúsculas. fuerza en [0, 1]."""
    palabras = []
    for palabra in texto.split():
        if palabra.lower() in ABREVIATURAS and rng.random() < fuerza:
            palabra = ABREVIATURAS[palabra.lower()]
        elif rng.random() < fuerza * 0.25:
            palabra = _palabra_con_error(rng, palabra)
        palabras.append(palabra)
    texto = " ".join(palabras)
    if rng.random() < 0.3 + fuerza * 0.4:
        texto = texto.translate(TILDES)
    caso = rng.random()
    if caso < 0.1 + fuerza * 0.2:
        texto = texto.upper()
    elif caso < 0.5:
        texto = texto.lower()
    if rng.random() < fuerza * 0.5:
        texto = texto.replace(".", rng.choice(["!!!", "...", "", " "]))
    return texto


def reporte(rng: random.Random, etiqueta: str, caso: str = "comun") -> str:
    frases = SOLO_PRUEBA[etiqueta] if caso == "frase_nueva" else SITUACIONES[etiqueta]
    partes = [rng.choice(frases)]
    menos_graves = ORDEN[ORDEN.index(etiqueta) + 1:]
    if menos_graves and rng.random() < 0.35:  # una situación secundaria menos grave
        partes.append(rng.choice(SITUACIONES[rng.choice(menos_graves)]))
    mas_graves = ORDEN[:ORDEN.index(etiqueta)]
    if mas_graves and (caso == "negacion" or rng.random() < 0.3):
        negaciones = NEGACIONES_PRUEBA if caso == "negacion" else NEGACIONES
        partes.insert(0, rng.choice(negaciones[rng.choice(mas_graves)]))
    rng.shuffle(partes)
    inicio, extra = rng.choice(INICIOS), rng.choice(EXTRAS)
    animal, lugar = rng.choice(ANIMALES), rng.choice(LUGARES)
    cuerpo = f"{animal} {lugar} {' y '.join(partes)}" if rng.random() < 0.6 else \
        f"{animal} {' y '.join(partes)} {lugar}"
    texto = " ".join(f"{inicio + ', ' if inicio else ''}{cuerpo}. {extra}".split())
    fuerza = 0.7 if caso == "ruido_fuerte" else rng.choice([0.0, 0.1, 0.25, 0.4])
    texto = ensuciar(rng, texto, fuerza)
    if len(texto) < 20:
        texto += " lo vi hoy"  # RN-01: 20 caracteres o más
    return texto


def generar(cantidad: int, semilla: int, casos: tuple[str, ...] = ("comun",),
            excluir: frozenset[str] = frozenset()) -> list[tuple[str, str, str]]:
    """(texto, prioridad, caso), balanceado por prioridad. Misma semilla, mismos datos."""
    rng = random.Random(semilla)
    filas: list[tuple[str, str, str]] = []
    vistos = set(excluir)
    i = 0
    while len(filas) < cantidad:
        etiqueta, caso = ORDEN[i % 4], casos[(i // 4) % len(casos)]
        i += 1
        if caso == "negacion" and etiqueta == "critica":
            etiqueta = "alta"  # no hay nada más grave que negar sobre un crítico
        texto = reporte(rng, etiqueta, caso)
        if texto not in vistos:
            vistos.add(texto)
            filas.append((texto, etiqueta, caso))
    return filas


def conjuntos() -> dict[str, list[tuple[str, str, str]]]:
    """Entrenamiento 6.000, validación 1.000 y prueba 1.200 (mitad casos difíciles), sin
    textos repetidos entre conjuntos."""
    entrenamiento = generar(6000, semilla=101)
    vistos = frozenset(t for t, _, _ in entrenamiento)
    validacion = generar(1000, semilla=202, excluir=vistos)
    vistos |= {t for t, _, _ in validacion}
    prueba = (generar(600, semilla=303, excluir=vistos)
              + generar(600, semilla=404, casos=("frase_nueva", "negacion", "ruido_fuerte"),
                        excluir=vistos))
    return {"entrenamiento": entrenamiento, "validacion": validacion, "prueba": prueba}


def escribir(filas: list[tuple[str, str, str]], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo, lineterminator="\n")
        escritor.writerow(["texto", "prioridad", "caso"])
        escritor.writerows(filas)


def leer(ruta: Path) -> list[tuple[str, str, str]]:
    with ruta.open(encoding="utf-8", newline="") as archivo:
        return [(f["texto"], f["prioridad"], f["caso"]) for f in csv.DictReader(archivo)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida-dir", default="scripts/ia/datos")
    parser.add_argument("--solo-prueba", action="store_true",
                        help="escribe solo el conjunto de prueba fijo")
    args = parser.parse_args()
    for nombre, filas in conjuntos().items():
        if args.solo_prueba and nombre != "prueba":
            continue
        escribir(filas, Path(args.salida_dir) / f"triaje_{nombre}.csv")
        print(f"{nombre}: {len(filas)} reportes")


if __name__ == "__main__":
    main()
