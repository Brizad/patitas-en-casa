# Trabajador local de video (#125)

El análisis de video no cabe en Render gratis (512 MB) y Hugging Face ya cobra los Spaces
Docker. Por eso corre en una PC del equipo: el trabajador **le pide** los videos a la API de
Render (no abre puertos ni recibe conexiones), los analiza y devuelve el resultado.

```
Ciudadano ──video──> API en Render ──(disco temporal)──┐
                          ^                            │ POST /video/trabajos/reclamar
                          │ resultado                  │ GET  /video/trabajos/{id}/archivo
                          └──────── trabajador local <─┘ (esta carpeta, en tu PC)
```

Cuadros (5 por segundo, OpenCV) → MediaPipe Object Detector (¿hay un perro o gato? ¿dónde?)
→ DeepLabCut SuperAnimal-Quadruped (39 puntos del cuerpo) → medidas de la marcha →
clasificador (MLP + reglas de seguridad) → prioridad, confianza, evidencias y una tira de 3
cuadros con los puntos dibujados. El video se borra apenas termina.

## Importante en Windows: Control inteligente de aplicaciones

En la PC de desarrollo, Windows 11 **bloqueó** las DLL de `torchvision` y de algunas versiones
de `scikit-learn` y `numba` («Una directiva de Control de aplicaciones bloqueó este archivo»).
DeepLabCut las necesita, así que **en Windows directo no arranca**. No se recomienda apagar
esa protección (en Windows 11 no se puede volver a encender sin reinstalar). La salida es
**WSL2** (Linux dentro de Windows), donde esa directiva no aplica:

1. PowerShell como administrador: `wsl --install -d Ubuntu-24.04` y reinicia.
2. Abre «Ubuntu» y sigue los pasos de Linux de abajo.

## Instalar (Linux o WSL2)

Usa una ruta corta (en Windows las rutas largas también fallaron al instalar).

```bash
sudo apt install -y python3-venv git libegl1 libgles2   # MediaPipe necesita libEGL
git clone https://github.com/Brizad/patitas-en-casa.git ~/patitas && cd ~/patitas/servicios/video
python3 -m venv ~/pv && source ~/pv/bin/activate
pip install torch==2.14.1 torchvision==0.29.2 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

La primera vez se descargan dos modelos a `~/.patitas-video` y a la carpeta de DeepLabCut:
EfficientDet-Lite0 de MediaPipe (≈ 14 MB) y SuperAnimal-Quadruped HRNet-w32 (≈ 118 MB).
**Licencia de SuperAnimal:** solo uso académico y no comercial (Mathis Lab, EPFL; citar a
Ye et al. 2023). Por eso no se sube al repositorio.

## Probar con un video tuyo

```bash
cd ~/patitas/servicios/video
python -m patitas_video.trabajador --video /mnt/c/Users/<tú>/Videos/perro.mp4
```

Muestra prioridad, confianza, evidencias y medidas. Si dice «no concluyente», revisa que el
perro o gato se vea de lado y completo la mayor parte del video.

## Trabajar contra Render

```bash
export PATITAS_API_URL=https://patitas-en-casa-pnnk.onrender.com
export PATITAS_VIDEO_TOKEN='<copia el valor de Render → Environment>'
python -m patitas_video.trabajador
```

- Mientras corre, consulta cada 15 s; si Render no responde, espera cada vez más (hasta 5 min).
- Si la PC está apagada más de 6 h, los videos que esperaban se borran y el reporte sigue con
  la prioridad del texto (falla segura).
- Mientras el trabajador consulta, Render no se duerme (consume horas del plan gratis: 750 al
  mes alcanzan para un servicio encendido todo el mes).
- El token nunca se imprime. No lo pegues en el código ni en un commit.

## Pruebas y reentrenamiento

- Las pruebas de esta carpeta corren en el CI de la API sin instalar nada pesado:
  `tests/test_video_marcha.py`, `test_video_clasificador.py` y `test_video_trabajador.py`.
- Prueba de humo con modelos reales: GitHub → Actions → «Video: prueba de humo» → Run
  workflow, con los enlaces de dos videos de licencia libre.
- Reentrenar con medidas etiquetadas por veterinarios (DT-04):
  `python entrenamiento/entrenar.py --datos medidas_etiquetadas.csv`.
