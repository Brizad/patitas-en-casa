# ruff: noqa: E501  (tabla de datos: una fila por animal se lee mejor sin cortar)
"""Publica los 22 animales del prototipo de adopción por la API normal, como coordinador (#422).

Uso (las credenciales nunca van en el código ni en la línea de comandos):

    $env:PATITAS_COORD_CORREO = "..."; $env:PATITAS_COORD_CLAVE = "..."   # o te las pide
    python scripts/operacion/publicar_animales_prototipo.py --url https://patitas-en-casa-pnnk.onrender.com \\
        --fotos C:\\ruta\\a\\docs\\prototipo\\fotos

Qué hace, por cada animal y en orden:
1. Si ya hay un animal con ese nombre en el refugio (publicado o no, presente o egresado), lo
   salta: nunca crea un duplicado ni modifica ni borra lo que ya existe. Por eso se puede correr
   dos veces. Si una corrida se corta entre el ingreso y la publicación, ese animal queda en el
   refugio sin publicar: se publica a mano desde el panel (Adopciones → Publicar).
2. Si no existe: registra el ingreso (respeta el cupo: sin cupo, la API responde 409 y el script
   se detiene y lista los que faltaron), lo publica con su ficha y sube su foto (máx. 300 KB).

Solo usa la biblioteca estándar. No imprime credenciales ni tokens.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib import error, parse, request

URL_PRODUCCION = "https://patitas-en-casa-pnnk.onrender.com"
FOTOS = Path(r"C:\Users\braya\Documents\Proyectos\patitas-en-casa\docs\prototipo\fotos")
# El ingreso pide el estado de salud y el prototipo no lo trae: se usa este (anotado en
# PLAN_CIERRE.md). El sexo del prototipo no tiene campo en la ficha: no se envía.
SALUD = "Sano, listo para adopción"


@dataclass(frozen=True)
class AnimalPrototipo:
    nombre: str
    especie: str
    edad_meses: int
    tamano: str
    energia: str
    ninos: bool
    otros: bool
    patio: bool
    niveles: tuple[int, int, int, int]  # cariño, energía, juego, calma
    etiquetas: tuple[str, str, str]
    peso: float
    peso_adulto: float
    descripcion: str
    foto: str

    def publicacion(self) -> dict:
        carino, energia, juego, calma = self.niveles
        return {"descripcion": self.descripcion, "tamano": self.tamano, "energia": self.energia,
                "edad_meses": self.edad_meses, "apto_ninos": self.ninos,
                "apto_otros_animales": self.otros, "necesita_patio": self.patio,
                "carino": carino, "energia_nivel": energia, "juego": juego, "calma": calma,
                "etiquetas": list(self.etiquetas), "peso_kg": self.peso,
                "peso_adulto_kg": self.peso_adulto}

    def ingreso(self) -> dict:
        texto = " ".join(self.etiquetas).lower()
        return {"nombre": self.nombre, "especie": self.especie, "estado_salud": SALUD,
                "vacunado": "vacunad" in texto, "esterilizado": "esterilizad" in texto}


A = AnimalPrototipo
ANIMALES = [  # «~5 años» se registra como 60 meses
    A("Toby", "perro", 3, "grande", "alta", True, True, True, (95, 92, 90, 38),
      ("Juguetón", "Guardián", "Vacunado"), 8, 35, "Aprende rápido y no suelta sus juguetes.", "toby.jpg"),
    A("Lupe", "perro", 60, "pequeno", "baja", True, True, False, (94, 45, 55, 95),
      ("Dormilona", "Cariñosa", "Tranquila"), 7, 7,
      "Le gusta muchísimo dormir. Su lugar favorito: cualquier cobija.", "lupe.jpg"),
    A("Winny", "perro", 84, "pequeno", "media", True, False, False, (90, 60, 58, 72),
      ("Atenta", "Leal", "Guardiana"), 5, 5, "Siempre pendiente de quién llega a la casa.", "winny.jpg"),
    A("Pinina", "perro", 72, "mediano", "media", True, True, False, (96, 70, 80, 75),
      ("Alegre", "Sonriente", "Sociable"), 10, 10, "Siempre sonriendo y lista para una caricia.", "pinina.jpg"),
    A("Luna", "gato", 12, "pequeno", "baja", True, False, False, (72, 55, 60, 90),
      ("Elegante", "Tranquila", "Esterilizada"), 3.5, 4.5,
      "Siempre bien vestida para la ocasión. Ama las siestas al sol.", "luna.jpg"),
    A("Copo", "perro", 24, "mediano", "media", True, True, False, (90, 74, 82, 70),
      ("Aventurera", "Sociable", "Vacunada"), 14, 16, "Le encantan las flores y los paseos largos.", "copo.jpg"),
    A("Max", "perro", 48, "grande", "alta", True, True, True, (98, 80, 88, 72),
      ("Sonriente", "Familiar", "Vacunado"), 30, 32, "Sonríe todo el día y adora a los niños.", "max.jpg"),
    A("Nube", "perro", 24, "grande", "alta", True, True, True, (85, 97, 92, 35),
      ("Energética", "Cantante", "Vacunada"), 20, 22, "Aúlla cuando está feliz. Necesita correr mucho.", "nube.jpg"),
    A("Chispa", "perro", 60, "pequeno", "media", False, False, False, (88, 70, 65, 60),
      ("Valiente", "Faldera", "Esterilizada"), 2.5, 3, "Pequeña pero valiente: te avisa de todo.", "chispa.jpg"),
    A("Bruno", "perro", 36, "mediano", "alta", True, True, False, (90, 88, 93, 50),
      ("Olfateador", "Juguetón", "Vacunado"), 12, 13, "Su nariz lo guía a todas partes.", "bruno.jpg"),
    A("Pancho", "perro", 6, "pequeno", "media", True, True, False, (96, 60, 78, 80),
      ("Dormilón", "Payaso", "Vacunado"), 5, 8, "Ronca un poquito y hace reír a todos.", "pancho.jpg"),
    A("Lola", "perro", 36, "pequeno", "baja", True, True, False, (94, 55, 70, 85),
      ("Mimosa", "Tranquila", "Esterilizada"), 6, 6, "Ideal para apartamento. Le encanta que la cepillen.", "lola.jpg"),
    A("Rocky", "perro", 12, "mediano", "media", True, True, False, (92, 78, 85, 65),
      ("Curioso", "Noble", "Vacunado"), 15, 18, "Peludo, noble y muy curioso.", "rocky.jpg"),
    A("Sombra", "gato", 24, "pequeno", "media", False, False, False, (70, 75, 80, 70),
      ("Misterioso", "Cazador", "Esterilizado"), 4, 4.5, "Aparece cuando menos lo esperas.", "sombra.jpg"),
    A("Humo", "gato", 36, "pequeno", "baja", True, True, False, (80, 45, 50, 95),
      ("Sereno", "Casero", "Esterilizado"), 5, 5, "Tranquilo, perfecto para quien llega en la noche.", "humo.jpg"),
    A("Pecas", "gato", 3, "pequeno", "alta", True, True, False, (85, 95, 98, 30),
      ("Traviesa", "Juguetona", "Vacunada"), 1, 4, "Persigue todo lo que se mueve.", "pecas.jpg"),
    A("Tigre", "gato", 12, "pequeno", "alta", True, True, False, (82, 80, 85, 60),
      ("Explorador", "Sociable", "Vacunado"), 3.8, 5, "Explora cada rincón y luego pide caricias.", "tigre.jpg"),
    A("Algodón", "gato", 4, "pequeno", "media", True, False, False, (90, 60, 70, 80),
      ("Dulce", "Tímida", "Vacunada"), 1.5, 4, "Al principio es tímida; luego no se despega.", "algodon.jpg"),
    A("Bombón", "perro", 24, "pequeno", "media", True, True, False, (97, 72, 85, 68),
      ("Payaso", "Mimoso", "Vacunado"), 4, 4, "Saca la lengua para todas las fotos.", "bombon.jpg"),
    A("Cascabel", "gato", 2, "pequeno", "alta", True, True, False, (88, 85, 92, 45),
      ("Curiosa", "Juguetona", "Vacunada"), 0.8, 4, "La oyes antes de verla: no se quita su cascabel.", "cascabel.jpg"),
    A("Mochi", "gato", 3, "pequeno", "media", True, True, False, (95, 55, 70, 82),
      ("Peluche", "Dulce", "Vacunado"), 1.2, 6, "Se deja cargar como un peluche.", "mochi.jpg"),
    A("Nieve", "gato", 2, "pequeno", "media", True, False, False, (86, 62, 72, 78),
      ("Esponjosa", "Tímida", "Vacunada"), 0.9, 4, "Una bolita de algodón con bigotes.", "nieve.jpg"),
]


class ErrorApi(Exception):
    def __init__(self, estado: int, detalle: str) -> None:
        super().__init__(f"{estado}: {detalle}")
        self.estado = estado


class Api:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.token: str | None = None

    def pedir(self, metodo: str, ruta: str, cuerpo: bytes | None = None,
              tipo: str | None = None, espera: int = 120):
        cabeceras = {"Accept": "application/json"}
        if tipo:
            cabeceras["Content-Type"] = tipo
        if self.token:
            cabeceras["Authorization"] = f"Bearer {self.token}"
        peticion = request.Request(self.base + ruta, data=cuerpo, headers=cabeceras, method=metodo)
        try:
            with request.urlopen(peticion, timeout=espera) as r:  # noqa: S310 (URL propia)
                datos = r.read()
                return json.loads(datos) if datos else None
        except error.HTTPError as e:
            try:
                detalle = json.loads(e.read()).get("detail", "")
            except ValueError:
                detalle = e.reason
            raise ErrorApi(e.code, str(detalle)) from None

    def json(self, metodo: str, ruta: str, datos: dict):
        return self.pedir(metodo, ruta, json.dumps(datos).encode(), "application/json")

    def entrar(self, correo: str, clave: str) -> None:
        cuerpo = parse.urlencode({"username": correo, "password": clave}).encode()
        self.token = self.pedir("POST", "/auth/token", cuerpo,
                                "application/x-www-form-urlencoded")["access_token"]

    def subir_foto(self, animal_id: int, archivo: Path) -> None:
        limite = f"----patitas{uuid.uuid4().hex}"
        tipo = "image/png" if archivo.suffix.lower() == ".png" else "image/jpeg"
        cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"foto\"; "
                  f"filename=\"{archivo.name}\"\r\nContent-Type: {tipo}\r\n\r\n").encode()
        cuerpo += archivo.read_bytes() + f"\r\n--{limite}--\r\n".encode()
        self.pedir("POST", f"/refugio/animales/{animal_id}/foto", cuerpo,
                   f"multipart/form-data; boundary={limite}")


def credenciales() -> tuple[str, str]:
    correo = os.environ.get("PATITAS_COORD_CORREO") or input("Correo del coordinador: ").strip()
    clave = os.environ.get("PATITAS_COORD_CLAVE") or getpass.getpass("Contraseña: ")
    return correo, clave


def publicar_todos(api: Api, fotos: Path | None, salida=print) -> dict[str, list[str]]:
    """Recorre ANIMALES en orden. Devuelve qué se publicó, qué se saltó y qué faltó."""
    resultado: dict[str, list[str]] = {"publicados": [], "saltados": [], "faltaron": []}
    en_refugio = api.pedir("GET", "/refugio/animales")
    for i, animal in enumerate(ANIMALES):
        if any(a["nombre"].casefold() == animal.nombre.casefold() for a in en_refugio):
            resultado["saltados"].append(f"{animal.nombre}: ya existe (no se modifica)")
            salida(f"· {animal.nombre}: ya existe, se salta")
            continue
        try:
            api.json("POST", "/refugio/ingresos", animal.ingreso())
            en_refugio = api.pedir("GET", "/refugio/animales")
            presente = max((a for a in en_refugio if a["nombre"] == animal.nombre),
                           key=lambda a: a["id"])
            api.json("POST", f"/refugio/animales/{presente['id']}/publicacion", animal.publicacion())
        except ErrorApi as e:
            motivo = "sin cupo en el refugio" if e.estado == 409 and "cupo" in str(e).lower() \
                else str(e)
            faltan = [a.nombre for a in ANIMALES[i:]]
            resultado["faltaron"] += [f"{n}: {motivo}" for n in faltan]
            salida(f"✗ {animal.nombre}: {motivo}. Se detiene; faltan: {', '.join(faltan)}")
            break
        nota = ""
        if fotos is not None:
            archivo = fotos / animal.foto
            try:
                api.subir_foto(presente["id"], archivo)
            except (OSError, ErrorApi) as e:
                nota = f" (sin foto: {e})"
        resultado["publicados"].append(animal.nombre + nota)
        salida(f"✓ {animal.nombre} publicado{nota}")
    return resultado


def main(argv: list[str] | None = None) -> int:
    opciones = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    opciones.add_argument("--url", default=URL_PRODUCCION)
    opciones.add_argument("--fotos", type=Path, default=FOTOS)
    opciones.add_argument("--sin-fotos", action="store_true")
    args = opciones.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # la consola de Windows no es UTF-8 por defecto
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    api = Api(args.url)
    api.entrar(*credenciales())
    r = publicar_todos(api, None if args.sin_fotos else args.fotos)
    print(f"\nPublicados: {len(r['publicados'])} · saltados: {len(r['saltados'])} · "
          f"faltaron: {len(r['faltaron'])}")
    for clave in ("saltados", "faltaron"):
        for linea in r[clave]:
            print(f"  {clave}: {linea}")
    return 1 if r["faltaron"] else 0


if __name__ == "__main__":
    sys.exit(main())
