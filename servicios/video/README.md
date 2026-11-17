# Trabajador local de video (#125)

## En 3 pasos (si nunca usaste Linux)

No necesitas saber Linux: solo vas a copiar y pegar dos líneas. Para pegar en la ventana de
Ubuntu usa **clic derecho** (Ctrl+V no siempre funciona ahí).

1. **Instala Ubuntu dentro de Windows (una sola vez).** Abre el menú Inicio, escribe
   `PowerShell`, clic derecho → *Ejecutar como administrador* y pega:
   `wsl --install -d Ubuntu-24.04`. Reinicia la PC. Abre la app **Ubuntu** desde el menú
   Inicio y elige un usuario y una contraseña (la contraseña no se ve al escribirla; es normal).
2. **Instala el trabajador (una sola vez, unos 20 min y 3 GB).** En la ventana de Ubuntu pega:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Brizad/patitas-en-casa/main/servicios/video/instalar_nodo.sh | bash
   ```
   Te pedirá la contraseña de Ubuntu del paso 1. Termina con «Listo».
3. **Arráncalo cada vez que quieras analizar videos.** Abre Ubuntu y pega:
   ```bash
   bash ~/patitas/servicios/video/arrancar_nodo.sh
   ```
   Te pide el token: en Render → servicio `patitas-en-casa` → *Environment* →
   `PATITAS_VIDEO_TOKEN` → ojo → copiar, y pégalo con clic derecho (no se verá). Puedes
   guardarlo para no pegarlo otra vez. Deja la ventana abierta; **Ctrl+C** la detiene.

Para probar con un video tuyo sin token (está en `C:\Users\<tú>\Videos\perro.mp4`):
`bash ~/patitas/servicios/video/arrancar_nodo.sh --video /mnt/c/Users/<tú>/Videos/perro.mp4`.
La salida dice también si se generó la vista previa del veterinario; añade
`--guardar-vista ~/vista.mp4` para guardarla y abrirla.

**¿El panel no muestra la vista previa?** (#231) Ya no hace falta adivinar: abre el reporte
en el panel. Mientras el video espera, el panel dice si este equipo está **apagado** o con una
**versión antigua**; cuando el análisis llega sin vista, dice el **motivo** (falta ffmpeg, la
API la rechazó, pasó de 5 MB…). La ventana de Ubuntu dice lo mismo tras cada análisis:
`vista previa del trabajo N subida (494 KB)` = todo bien. En ningún caso se pierde el resultado.

**Actualizar.** `arrancar_nodo.sh` se pone al día solo con `main` antes de trabajar (si
cambiaron las librerías, las instala). Para que eso funcione en un nodo instalado antes del
16-nov-2026, **repite el paso 2 una sola vez** (deja la marca `~/.patitas-video/carpeta` e
instala ffmpeg). Un nodo que ya corre sigue con el código viejo: **Ctrl+C y arráncalo otra
vez**. Si copiaste archivos a mano en `~/patitas`, no se pierden: quedan en `git stash list`.
Arrancar sin actualizar: `PATITAS_SIN_ACTUALIZAR=1 bash ~/patitas/servicios/video/arrancar_nodo.sh`.
Para olvidar el token guardado: `rm ~/.patitas-video/token`.

**¿Qué pasa si…?**

| Situación | Qué hace el sistema |
|---|---|
| Render se reinicia (cada despliegue, 1 a 3 min) | El nodo reintenta la vista y la entrega (5, 15, 45 y 120 s) sin volver a analizar |
| El PC se apaga a mitad de un análisis | A los 10 min la API vuelve a ofrecer el trabajo; el video espera en PostgreSQL hasta 6 h |
| El PC está apagado más de 6 h | El video se borra y el reporte sigue con la prioridad del texto (falla segura) |
| El equipo es lento (más de 8 min por video) | Entrega «no concluyente»: el veterinario decide con la descripción |
| La API rechaza un resultado | Queda como fallo con el motivo; el nodo sigue con el siguiente |
| El token está mal | El nodo se detiene y lo dice: copia otra vez `PATITAS_VIDEO_TOKEN` de Render |

## Cómo funciona

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

## Instalar a mano (Linux o WSL2)

Es lo mismo que hace `instalar_nodo.sh`. Usa una ruta corta (en Windows las rutas largas también fallaron al instalar).

```bash
sudo apt install -y python3-venv git libegl1 libgles2 ffmpeg   # MediaPipe necesita libEGL
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
