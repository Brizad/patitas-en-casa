# Preguntas probables de la sustentación (con respuesta corta)

Treinta preguntas que un profesor de Ingeniería de Software II suele hacer, agrupadas por
tema. Las respuestas son cortas a propósito: dilas con tus palabras y, si te piden más,
abre el archivo que se indica.

## Arquitectura

1. **¿Qué arquitectura usa el sistema?**
   Un monolito modular en capas: API (FastAPI) → servicios con las reglas de negocio →
   repositorios (interfaces) → PostgreSQL. Las reglas no dependen del framework ni de la base
   (puertos y adaptadores). `tests/test_arquitectura.py` lo comprueba en cada CI.

2. **¿Por qué un monolito y no microservicios?**
   Un solo desarrollador, pocos usuarios (RNF-14: 200 reportes/hora) y un servidor gratis de
   512 MB. Los microservicios suman red, despliegues y fallos parciales sin beneficio aquí.
   Los módulos (`reportes`, `rescates`, `cupos`, `adopciones`…) ya están separados por si un
   día hay que partirlo.

3. **¿Qué es un repositorio y por qué hay dos versiones de cada uno?**
   Un objeto que guarda y busca entidades. La versión en memoria sirve para pruebas rápidas
   y la de PostgreSQL para producción. Las *pruebas de contrato* ejecutan las mismas pruebas
   contra las dos para que se comporten igual.

4. **¿Cómo viaja un reporte desde el celular hasta la cola del veterinario?**
   PWA → `POST /reportes` → `ServicioReportes` valida RN-01 → `ServicioTriaje` clasifica
   (reglas + modelo, límite de 10 s) → se aplica RN-02/RN-03 → `RepositorioPostgres` lo
   guarda → `GET /cola` lo ordena por gravedad.

5. **¿Qué pasa si el clasificador se cae?**
   Falla segura (RN-03): el reporte queda en prioridad alta, estado «sin clasificar» y pasa a
   revisión humana. Si el JSON del modelo no carga, el triaje sigue solo con reglas.

6. **¿Qué es el outbox y por qué se usó?**
   Al confirmar un caso grave, los avisos a los rescatistas se guardan como «pendientes» en
   la misma transacción que la decisión, y un procesador los envía con reintentos. Si el
   correo falla, el aviso no se pierde y la pantalla nunca dice «se avisó» si no es cierto.

7. **¿Cómo se despliega?**
   Docker (una imagen con la API, la PWA y el panel compilado) en Render, descrito en
   `render.yaml`. Cada merge a `main` se despliega solo y la imagen aplica las migraciones
   al arrancar.

## Base de datos

8. **¿Por qué PostgreSQL?**
   Transacciones, restricciones (CHECK, únicos parciales, llaves foráneas), JSONB y
   disparadores; además es lo que ofrece Render gratis.

9. **¿Qué es una migración?**
   Un archivo de Alembic que lleva la base de una versión a la siguiente (`upgrade`) y sabe
   deshacerse (`downgrade`). Hay 20 en `migraciones/versions/`. Una prueba verifica que el
   esquema migrado coincide con `app/bd/esquema.py`.

10. **¿Cómo se evita que dos ingresos simultáneos superen la capacidad?**
    Con un `UPDATE refugios SET ocupados = ocupados + 1 WHERE ocupados < capacidad`.
    PostgreSQL bloquea la fila: solo uno pasa la condición. El CHECK de la tabla es la última
    barrera. Hay una prueba de concurrencia real.

11. **¿Cómo se garantiza que un rescate tenga un solo rescatista (RN-08)?**
    Con índices únicos parciales en la tabla `rescates`: uno por reporte vigente y uno por
    rescatista activo. Aunque el código fallara, la base lo impide.

12. **¿Y que un animal no se adopte dos veces (RN-11)?**
    Índice único parcial `uq_solicitudes_aprobada` (solo filas aprobadas). Aprobar es una
    transacción: si el índice salta, no queda nada a medias.

13. **¿Por qué las reglas de negocio están en el código Y en la base?**
    Defensa en profundidad: el código da mensajes claros; la base garantiza la regla aunque
    alguien entre por otro camino o haya un error.

## Seguridad

14. **¿Cómo se guardan las contraseñas?**
    Solo el hash Argon2id (lento y con sal). Nunca la contraseña. Mínimo 12 caracteres.

15. **¿Cómo funciona el inicio de sesión?**
    `POST /auth/token` devuelve un JWT firmado (HS256, 30 minutos). El navegador lo envía en
    `Authorization: Bearer`. En cada petición se valida la firma y se relee la cuenta, así una
    cuenta suspendida pierde el acceso al instante.

16. **¿Qué es RBAC aquí?**
    Cada endpoint declara qué roles lo usan (`exigir_rol`): 401 sin sesión, 403 con otro rol.
    El panel oculta botones, pero la seguridad real está en el servidor.

17. **¿Cómo se frena un ataque de fuerza bruta?**
    5 fallos por correo o 20 por IP en 15 minutos → 429 con `Retry-After` (DT-06), sin mirar
    la contraseña mientras dura el bloqueo.

18. **¿Cómo se protege la privacidad del ciudadano?**
    No necesita cuenta. El seguimiento público solo muestra pasos y fechas (RN-14). El
    contacto opcional se guarda cifrado con AES-256-GCM. Los indicadores y exportaciones no
    llevan datos personales.

19. **¿Cómo se evita subir secretos al repositorio?**
    `.env` está en `.gitignore`, los secretos viven en variables de entorno de Render, y el
    CI ejecuta gitleaks sobre todo el historial (con una auto-prueba que confirma que detecta
    un token falso).

20. **¿Qué es la bitácora y por qué es inmutable?**
    Registra quién hizo qué cambio y cuándo, sin el cuerpo de la petición. Un disparador de
    PostgreSQL rechaza `UPDATE` y `DELETE`: la historia no se puede reescribir (RF-32).

## Inteligencia artificial

21. **¿Qué modelo de IA usa el triaje?**
    TF-IDF + regresión logística sobre el texto, combinado con reglas validadas. 61 KB,
    0,05 ms por reporte, sin scikit-learn en producción (cabe en 512 MB).

22. **¿Con qué datos se entrenó?**
    Con datos **sintéticos** generados por `scripts/ia/generar_datos_sinteticos.py`, porque no
    hay reportes reales etiquetados. Sus métricas (0,99) no son clínicas: prueban que el
    camino funciona. Se reentrena con la bitácora (prioridad confirmada = etiqueta).

23. **¿Por qué el modelo solo puede subir la prioridad?**
    Porque se entrenó con datos sintéticos y las reglas ya protegen los críticos conocidos.
    Así nunca empeora el recall de «crítica» (RNF-03): ante la duda, más urgencia o revisión
    humana.

24. **¿Cómo explica la IA sus sugerencias (RNF-09)?**
    Con al menos 3 evidencias: las palabras que más pesaron hacia la prioridad elegida y lo
    que opinó cada parte (reglas y modelo).

25. **¿Cómo funciona la compatibilidad adoptante–animal y por qué no discrimina?**
    Puntaje de 0 a 100 con cinco factores (espacio, tiempo solo, experiencia, niños, otros
    animales) y 3 razones. Solo usa datos del hogar y del animal; el perfil ni pide edad,
    género, estrato ni ingresos (RNF-16), y una prueba lo verifica.

26. **¿Qué resuelve el algoritmo húngaro?**
    En una jornada, la combinación persona–animal que maximiza la compatibilidad total. El
    reparto voraz puede dar menos (ejemplo de la prueba: 100 contra 165).

## Pruebas y calidad

27. **¿Cómo se prueba el sistema?**
    Más de 560 pruebas con pytest: unitarias, de contrato (memoria y PostgreSQL), de caja negra
    de la API, de migraciones, de concurrencia y de arquitectura. El panel con vitest.
    Cobertura del 98 % (el CI exige 70 %).

28. **¿Qué hace el CI en cada PR?**
    gitleaks (secretos), Ruff (estilo, errores y complejidad ≤ 10), pytest con PostgreSQL real
    y cobertura mínima, y pruebas + compilación del panel. Si algo falla, no se integra.

29. **¿Cómo trabajaste el flujo de cambios?**
    Issue → rama → pruebas primero → PR pequeño (≤ 300 líneas) que cita el issue → CI en
    verde → revisión → merge. Registro en `CHANGELOG.md` y en `DEUDA_TECNICA.md`.

30. **¿Qué quedó sin hacer y por qué?**
    El video ya se analiza (fase 6) con un trabajador local, pero su modelo usa datos
    sintéticos y no está validado con veterinarios (DT-04). La
    disponibilidad del 99 % (RNF-04) tampoco se garantiza en el plan gratis (el servicio se
    duerme). La prueba con usuarios reales (RNF-06) requiere participantes. Todo está en
    `docs/aprende/trazabilidad.md` con su motivo.

## Análisis de video (fase 6, v1.1.0)

31. **¿Cómo se analiza el video si Render gratis no tiene memoria para eso?**
    Con un trabajador local en una PC del equipo. Render guarda el video unos minutos en su
    disco temporal y lo pone en una cola (`analisis_video`). El trabajador pide trabajos cada
    15 s con un token compartido, descarga el video, lo analiza y devuelve el resultado. No
    abre puertos: él llama a Render.

32. **¿Por qué no MediaPipe Pose?**
    Porque solo detecta el cuerpo humano (33 puntos). Se usa MediaPipe Object Detector para
    encontrar al perro o gato y DeepLabCut SuperAnimal-Quadruped (preentrenado, 39 puntos de
    cuadrúpedos) para el cuerpo; con esos puntos se mide la marcha.

33. **¿Qué mide el sistema en la marcha?**
    Si el animal está de pie, si apoya las cuatro patas, la asimetría entre patas pareadas
    (cojera), la regularidad del paso y cuánto se desplaza; todo dividido por el largo del
    cuerpo para que no dependa de la distancia a la cámara. Cada umbral está en `marcha.py`.

34. **¿Qué pasa si el video no sirve o el trabajador está apagado?**
    Falla segura: si no se ve un perro o gato, o el cuerpo no se ve completo, el resultado es
    «no concluyente»; si el video se pierde o nadie lo analiza en 6 h, «fallido». En todos los
    casos el reporte sigue con la prioridad del texto y el video se borra.

35. **¿Cómo se protege la privacidad del video?**
    Solo el teléfono que creó el reporte puede subirlo (su clave de idempotencia, 30 min, una
    vez). El video nunca se publica ni se guarda para siempre. Quedan las medidas, las
    evidencias y una tira de 3 cuadros que solo ve el personal con sesión (RN-14, RNF-08).
