# Mapa del proyecto para estudiarlo

Esta carpeta es la guía de estudio de Patitas en Casa. Está escrita para preparar la
sustentación: qué hace cada parte, por qué se hizo así y cómo comprobarlo uno mismo.

## La idea en una frase

Un ciudadano reporta un animal en emergencia sin crear cuenta. La IA sugiere una prioridad,
un veterinario la confirma, un rescatista va por el animal y el refugio controla sus cupos.
Después el animal puede darse en adopción.

## Las capas (de afuera hacia adentro)

```
Navegador ── PWA ciudadana (app/pwa)        Panel del personal (panel/, React)
                 │                                   │
                 └──────────── HTTP/JSON ────────────┘
                                 │
API (app/api/main.py) ── valida la entrada, exige sesión y rol, traduce errores a 4xx
                                 │
Servicios (casos de uso) ── app/reportes, app/rescates, app/cupos, app/usuarios, app/triaje
                                 │   (reglas de negocio RN-xx; no saben nada de HTTP ni SQL)
Repositorios (puertos) ── Protocol de Python con dos versiones: en memoria y PostgreSQL
                                 │
PostgreSQL ── tablas en app/bd/esquema.py, cambios con Alembic (migraciones/)
```

¿Por qué así? Las reglas de negocio quedan en un solo lugar (los servicios) y se pueden
probar sin base de datos, usando el repositorio en memoria. La prueba
`tests/test_arquitectura.py` verifica que el núcleo no importe FastAPI ni SQLAlchemy.

## Orden recomendado para estudiar

1. `app/dominio/modelos.py`: las palabras del negocio (Reporte, Prioridad, Rescate…).
2. `app/reportes/servicio.py` y `app/triaje/`: cómo entra un reporte y cómo se clasifica.
3. `app/api/main.py`: los endpoints. Busca `@app.post("/reportes")` y sigue la llamada.
4. `app/reportes/repositorio.py` (memoria) y luego `repositorio_postgres.py` (SQL).
5. `app/bd/esquema.py` y `migraciones/versions/`: las tablas y su historia.
6. `app/usuarios/`, `app/seguridad/tokens.py`, `app/api/seguridad.py`: cuentas, JWT y roles.
7. `app/rescates/` y `app/avisos/`: el rescate y el envío de avisos con reintentos.
8. `panel/src/`: el panel en React. Empieza por `App.tsx` y `api.ts`.
9. `app/adopciones/`, `app/indicadores/`, `app/bitacora/`: adopción, indicadores y
   bitácora (fases 3 y 5).
10. `scripts/ia/` y `app/triaje/modelo.py`: la IA entrenada (fase 4).
11. `tests/`: cada archivo de prueba es un ejemplo de uso. Lee `test_api.py`.
12. Las guías por fase de esta carpeta, en orden: `fase-1-pantallas-por-rol.md`,
    `fase-2-refugio-completo.md`, `fase-3-adopcion.md`, `fase-4-ia.md`, `fase-5-cierre.md`.

## Cómo probarlo en tu PC

```bash
.venv\Scripts\activate
pytest -q                                   # todas las pruebas
uvicorn --factory app.api.main:crear_app --reload
# http://127.0.0.1:8000/docs  (documentación interactiva de la API)
cd panel && npm run dev                     # panel en http://127.0.0.1:5173/panel/
```

## Glosario

- **API REST**: el servidor recibe peticiones HTTP (GET para leer, POST para crear, PUT para
  reemplazar) y responde JSON. El código de estado dice cómo le fue: 2xx bien, 4xx error del
  cliente (401 sin sesión, 403 sin permiso, 404 no existe, 409 conflicto, 422 datos no
  válidos), 5xx error del servidor.
- **FastAPI**: el framework de Python con el que se escribe la API. Valida la entrada con
  Pydantic y genera la documentación en `/docs`.
- **Pydantic**: describe la forma de los datos de entrada (`class ReporteEntrada(BaseModel)`)
  y rechaza con 422 lo que no cumple.
- **Repositorio**: objeto que guarda y busca entidades. El servicio no sabe si detrás hay una
  lista en memoria o PostgreSQL.
- **Protocol**: interfaz de Python. Dice qué métodos debe tener un repositorio.
- **Prueba de contrato**: la misma prueba se ejecuta contra la versión en memoria y la de
  PostgreSQL, para que se comporten igual.
- **SQLAlchemy Core**: librería para escribir SQL desde Python sin ORM (sin clases mapeadas).
- **Migración (Alembic)**: archivo que cambia la base de una versión a la siguiente
  (`upgrade`) y sabe deshacerse (`downgrade`). Así la base de todos queda igual.
- **Transacción**: grupo de cambios que se guardan todos o ninguno.
- **UPDATE condicional**: `UPDATE refugios SET ocupados = ocupados + 1 WHERE ocupados <
  capacidad`. Si dos personas ingresan a la vez el último cupo, solo una lo logra.
- **Outbox (bandeja de salida)**: en vez de enviar el correo dentro de la petición, se guarda
  el aviso como «pendiente» en la misma transacción y otro proceso lo envía con reintentos.
  Si el correo falla, el aviso no se pierde.
- **Argon2id**: algoritmo para guardar contraseñas como hash lento y con sal. Nunca se guarda
  la contraseña.
- **JWT (JSON Web Token)**: texto firmado que el servidor entrega al iniciar sesión. El
  navegador lo envía en `Authorization: Bearer <token>`. Como está firmado, el servidor sabe
  que no fue alterado. Vence a los 30 minutos.
- **RBAC (control de acceso por rol)**: cada endpoint dice qué roles lo usan
  (veterinario, coordinador, rescatista, administrador). `exigir_rol` responde 401 sin sesión
  y 403 con un rol sin permiso.
- **Idempotencia**: repetir la misma petición no crea un duplicado (`Idempotency-Key`).
- **PWA**: página web que se puede instalar en el teléfono y funciona sin conexión.
- **CSP (Content-Security-Policy)**: encabezado que prohíbe scripts de otros sitios (XSS).
- **CI (integración continua)**: GitHub Actions ejecuta gitleaks, Ruff, pytest y el build del
  panel en cada PR (también en los PR apilados que apuntan a otra rama). Si algo falla, no se integra.
- **Render**: plataforma donde se despliega la imagen de Docker. `render.yaml` describe la
  base y el servicio; cada cambio en `main` se despliega solo.
- **Docker**: empaqueta la API con todo lo que necesita para que corra igual en cualquier PC.
- **Datos sintéticos**: datos inventados por un programa, con reglas conocidas, para entrenar
  o probar cuando no hay datos reales.
- **TF-IDF**: convierte un texto en números: cuenta cada palabra y le da más peso si es rara
  en el conjunto (una palabra que aparece en todos los reportes no ayuda a distinguir).
- **Regresión logística**: modelo que da una probabilidad por clase sumando pesos de cada
  palabra; los pesos se aprenden de los ejemplos.
- **Recall (sensibilidad)**: de todos los casos críticos reales, cuántos detectó el modelo.
- **Algoritmo húngaro**: resuelve el problema de asignación (quién con qué) maximizando el
  total.
- **Middleware**: código que se ejecuta antes y después de cada petición (aquí: cabeceras de
  seguridad y bitácora).
- **Disparador (trigger)**: función de la base que se ejecuta sola ante un INSERT, UPDATE o
  DELETE (aquí: impedir cambiar la bitácora).
- **Anonimizar**: quitar todo dato que permita identificar a una persona o un lugar.

## Archivos de esta carpeta

- `00-mapa.md`: este archivo.
- `fase-N-<tema>.md`: una guía por fase del plan.
- `avance.md`: qué quedó, qué falta y la URL de Render.
- `preguntas-para-brayan.md`: decisiones que tomé solo y que Brayan debe revisar.
