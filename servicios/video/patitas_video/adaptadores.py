"""Adaptadores reales del análisis (#125): OpenCV, MediaPipe y DeepLabCut.

Solo los importa el trabajador local (requirements.txt de esta carpeta); el CI de la API no
los instala. Las versiones probadas están fijadas en requirements.txt.

- MediaPipe Object Detector (EfficientDet-Lite0, clases COCO): MediaPipe Pose NO sirve aquí,
  porque solo conoce el cuerpo humano (33 puntos de una persona).
- DeepLabCut SuperAnimal-Quadruped (HRNet-w32, EPFL): 39 puntos del cuadrúpedo, sin
  entrenar nada. Licencia de los pesos: solo uso académico y no comercial; se descargan en
  la PC del trabajador y no se suben al repositorio.
"""
from __future__ import annotations

import contextlib
import shutil
import subprocess
import tempfile
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from patitas_video.analisis import FPS, Caja, analizar
from patitas_video.clasificador import ClasificadorMarcha
from patitas_video.marcha import UMBRAL_PUNTO, Cuadro

CARPETA_MODELOS = Path.home() / ".patitas-video"
URL_DETECTOR = ("https://storage.googleapis.com/mediapipe-models/object_detector/"
                "efficientdet_lite0/float32/latest/efficientdet_lite0.tflite")
ANCHO_MAXIMO = 960  # se reduce el cuadro: más rápido y suficiente para ver la marcha
ALTO_TIRA = 120
MAX_TIRA = 190 * 1024  # la API acepta hasta 200 KB
ALTO_VISTA = 480  # vista previa del veterinario: 480p, ~10 fps, H.264, <= 5 MB
FPS_VISTA = 10
MAX_VISTA = 5 * 1024 * 1024
UNIONES = (("neck_base", "back_middle"), ("back_middle", "tail_base"),
           ("front_left_knee", "front_left_paw"), ("front_right_knee", "front_right_paw"),
           ("back_left_knee", "back_left_paw"), ("back_right_knee", "back_right_paw"))


class LectorOpenCV:
    def cuadros(self, ruta: str, fps: float) -> Iterator[np.ndarray]:
        video = cv2.VideoCapture(ruta)
        try:
            original = video.get(cv2.CAP_PROP_FPS) or 30.0
            paso, siguiente, indice = original / fps, 0.0, 0
            while True:
                leido, cuadro = video.read()
                if not leido:
                    return
                if indice >= siguiente:
                    siguiente += paso
                    alto, ancho = cuadro.shape[:2]
                    if ancho > ANCHO_MAXIMO:
                        escala = ANCHO_MAXIMO / ancho
                        cuadro = cv2.resize(cuadro, (ANCHO_MAXIMO, round(alto * escala)))
                    yield cv2.cvtColor(cuadro, cv2.COLOR_BGR2RGB)
                indice += 1
        finally:
            video.release()


class DetectorMediaPipe:
    def __init__(self, umbral: float = 0.35) -> None:
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import ObjectDetector, ObjectDetectorOptions

        modelo = CARPETA_MODELOS / "efficientdet_lite0.tflite"
        if not modelo.exists():
            CARPETA_MODELOS.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(URL_DETECTOR, modelo)  # URL fija de Google
        self._mp = mp
        self._detector = ObjectDetector.create_from_options(ObjectDetectorOptions(
            base_options=BaseOptions(model_asset_path=str(modelo)), score_threshold=umbral,
            category_allowlist=["dog", "cat"], max_results=1))

    def cerrar(self) -> None:
        """Hay que llamarlo antes de salir: si MediaPipe se cierra solo mientras Python se
        apaga, falla con «'NoneType' object is not callable» (visto en la prueba de humo)."""
        self._detector.close()

    def detectar(self, imagen: np.ndarray) -> Caja | None:
        resultado = self._detector.detect(self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(imagen)))
        if not resultado.detections:
            return None
        d = resultado.detections[0]
        caja, categoria = d.bounding_box, d.categories[0]
        return Caja(caja.origin_x, caja.origin_y, caja.width, caja.height,
                    categoria.category_name, categoria.score)


class EstimadorDeepLabCut:
    def __init__(self, modelo: str = "hrnet_w32") -> None:
        from deeplabcut.pose_estimation_pytorch.apis.utils import get_pose_inference_runner
        from deeplabcut.pose_estimation_pytorch.config.pose import PoseConfig
        from deeplabcut.pose_estimation_pytorch.modelzoo.utils import (
            get_super_animal_snapshot_path,
        )

        configuracion = PoseConfig.build_for_superanimal_inference(
            "superanimal_quadruped", model_name=modelo, detector_name=None,
            max_individuals=1, device="cpu")
        pesos = get_super_animal_snapshot_path("superanimal_quadruped", modelo)
        self._nombres = list(configuracion["metadata"]["bodyparts"])
        self._runner = get_pose_inference_runner(configuracion, snapshot_path=pesos,
                                                 max_individuals=1, device="cpu")

    def puntos(self, imagen: np.ndarray, caja: Caja) -> Cuadro:
        contexto = {"bboxes": np.array([[caja.x, caja.y, caja.ancho, caja.alto]], dtype=float),
                    "bbox_scores": np.array([caja.puntaje], dtype=float)}
        prediccion = self._runner.inference([(imagen, contexto)])[0]
        return {nombre: (float(x), float(y), float(c)) for nombre, (x, y, c)
                in zip(self._nombres, prediccion["bodyparts"][0], strict=True)}


def dibujar_esqueleto(imagen: np.ndarray, puntos: Cuadro | None) -> np.ndarray:
    """La imagen en BGR con las uniones y los puntos confiables de DeepLabCut encima."""
    lienzo = cv2.cvtColor(imagen, cv2.COLOR_RGB2BGR)
    visibles = {k: (int(x), int(y)) for k, (x, y, c) in (puntos or {}).items()
                if c >= UMBRAL_PUNTO}
    for a, b in UNIONES:
        if a in visibles and b in visibles:
            cv2.line(lienzo, visibles[a], visibles[b], (0, 200, 255), 3)
    for punto in visibles.values():
        cv2.circle(lienzo, punto, 5, (0, 255, 0), -1)
    return lienzo


class EscritorVistaFfmpeg:
    """Vista previa para el veterinario (decisión del autor, cambia RNF-08): MP4 H.264 a 480p y
    10 fps con el esqueleto dibujado. Cada cuadro analizado (5 por segundo) se escribe dos
    veces. Necesita ffmpeg en el PATH (en WSL2: sudo apt install ffmpeg). El cuadro va por la
    entrada estándar de ffmpeg: nunca se acumula el video en memoria."""

    def __init__(self) -> None:
        self._carpeta = Path(tempfile.mkdtemp(prefix="patitas-vista-"))
        self._ruta = self._carpeta / "vista.mp4"
        self._proceso: subprocess.Popen | None = None
        self._tamano: tuple[int, int] | None = None

    def _iniciar(self, ancho: int, alto: int) -> subprocess.Popen:
        orden = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                 "-s", f"{ancho}x{alto}", "-r", str(FPS_VISTA), "-i", "-", "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-maxrate", "600k",
                 "-bufsize", "1200k", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                 str(self._ruta)]
        return subprocess.Popen(orden, stdin=subprocess.PIPE)

    def escribir(self, imagen: np.ndarray, puntos: Cuadro | None) -> None:
        lienzo = dibujar_esqueleto(imagen, puntos)
        if self._tamano is None:
            alto = ALTO_VISTA
            ancho = round(lienzo.shape[1] * alto / lienzo.shape[0]) // 2 * 2  # par, para H.264
            self._tamano = (ancho, alto)
            self._proceso = self._iniciar(ancho, alto)
        lienzo = cv2.resize(lienzo, self._tamano)
        for _ in range(FPS_VISTA // FPS):
            self._proceso.stdin.write(lienzo.tobytes())

    def terminar(self) -> bytes | None:
        try:
            if self._proceso is None:
                return None
            self._proceso.stdin.close()
            if self._proceso.wait(timeout=120) != 0 or not self._ruta.is_file():
                return None
            datos = self._ruta.read_bytes()
            return datos if len(datos) <= MAX_VISTA else None
        finally:
            self.cancelar()

    def cancelar(self) -> None:
        if self._proceso is not None and self._proceso.poll() is None:
            self._proceso.kill()
        if self._proceso is not None and self._proceso.stdin is not None:
            with contextlib.suppress(OSError):
                self._proceso.stdin.close()
        shutil.rmtree(self._carpeta, ignore_errors=True)  # RNF-08: nada queda en el disco


class DibujanteOpenCV:
    def tira(self, muestras: list[tuple[np.ndarray, Cuadro]]) -> bytes:
        cuadros = []
        for imagen, puntos in muestras:
            lienzo = dibujar_esqueleto(imagen, puntos)
            escala = ALTO_TIRA / lienzo.shape[0]
            cuadros.append(cv2.resize(lienzo, (round(lienzo.shape[1] * escala), ALTO_TIRA)))
        tira = np.hstack(cuadros)
        while True:
            listo, png = cv2.imencode(".png", tira)
            if not listo:
                raise RuntimeError("no se pudo crear la tira de cuadros")
            if len(png) <= MAX_TIRA:
                return png.tobytes()
            tira = cv2.resize(tira, None, fx=0.8, fy=0.8)


class AnalizadorCompleto:
    def __init__(self) -> None:
        self.lector, self.detector = LectorOpenCV(), DetectorMediaPipe()
        self.estimador, self.clasificador = EstimadorDeepLabCut(), ClasificadorMarcha.desde_json()
        self.dibujante = DibujanteOpenCV()

    def __call__(self, ruta: str) -> dict:
        vista = EscritorVistaFfmpeg() if shutil.which("ffmpeg") else None  # sin ffmpeg, sin vista
        return analizar(ruta, self.lector, self.detector, self.estimador, self.clasificador,
                        self.dibujante, vista)

    def cerrar(self) -> None:
        self.detector.cerrar()


def analizador_completo() -> AnalizadorCompleto:
    return AnalizadorCompleto()
