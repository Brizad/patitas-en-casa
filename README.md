# Patitas en Casa

[![CI](https://github.com/Brizad/patitas-en-casa/actions/workflows/ci.yml/badge.svg)](https://github.com/Brizad/patitas-en-casa/actions/workflows/ci.yml)

Plataforma web inteligente para la gestión logística de refugios animales en Cúcuta
(Norte de Santander): triaje de emergencias de perros y gatos, control de cupos y,
en próximos incrementos, recomendación de adopciones.

Proyecto integrador — Ingeniería de Software II (grupo CR), Universidad de Pamplona.
Autor: Brayan David Amado Ramírez.

## Estado: v0.1.0 publicada; incremento 2 ("Fundación segura") en `main`

Públicos (el ciudadano no necesita cuenta):
- `POST /reportes`: reporte de emergencia (descripción, ubicación, video opcional).
- `GET /reportes/{codigo}`: estado del reporte con el código de seguimiento.

Personal (veterinario o coordinador), con `Authorization: Bearer <token>`:
- `POST /auth/token`: inicio de sesión (formulario `username` = correo, `password`).
- `GET /auth/yo`: datos de la sesión.
- `GET /cola`: cola priorizada de reportes.
- `POST /refugio/ingresos` y `GET /refugio/ocupacion`: cupos del refugio.

## Cómo ejecutarlo

Requisitos: Python 3.11+ y PostgreSQL 17 con dos bases vacías, `patitas` (aplicación) y
`patitas_test` (pruebas: se vacía en cada ejecución).

```bash
python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # en Windows: copy .env.example .env  (y escribe tu contraseña)
alembic upgrade head               # crea las tablas en la base patitas
pytest --cov=app                   # pruebas con cobertura (sin PostgreSQL, las de base se omiten)
uvicorn --factory app.api.main:crear_app --reload  # documentación en http://127.0.0.1:8000/docs
```

El archivo `.env` nunca se sube al repositorio. Además de la contraseña de PostgreSQL necesita
`PATITAS_JWT_SECRETO`, una clave aleatoria para firmar las sesiones:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Para crear una cuenta de personal (la contraseña se pide sin mostrarla, mínimo 12 caracteres):

```bash
python -m app.usuarios.crear_usuario --correo ana@refugio.co --nombre "Ana" --rol veterinario
```

En `http://127.0.0.1:8000/docs`, el botón **Authorize** inicia sesión con ese correo y contraseña.

Cada cambio en `app/bd/esquema.py` necesita una migración nueva en `migraciones/versions/`.

## Flujo de trabajo

GitHub Flow: ramas cortas (`feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`) desde `main`,
integración por Pull Request con CI en verde y versiones etiquetadas según SemVer.
Ver `CHANGELOG.md` y `DEUDA_TECNICA.md`.

## Seguimiento del proyecto

Tablero Scrum (GitHub Projects): https://github.com/users/Brizad/projects/1

Backlog con historias de usuario, bug y deuda técnica: https://github.com/Brizad/patitas-en-casa/issues

Versión publicada: https://github.com/Brizad/patitas-en-casa/releases/tag/v0.1.0

La rama `main` está protegida: todo cambio entra por Pull Request y solo se integra con el check `build-lint-test` en verde (gitleaks, Ruff y pytest con PostgreSQL).
