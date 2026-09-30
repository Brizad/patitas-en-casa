# Patitas en Casa

Plataforma web inteligente para la gestión logística de refugios animales en Cúcuta
(Norte de Santander): triaje de emergencias de perros y gatos, control de cupos y,
en próximos incrementos, recomendación de adopciones.

Proyecto integrador — Ingeniería de Software II (grupo CR), Universidad de Pamplona.
Autor: Brayan David Amado Ramírez.

## Estado: v0.1.0 (primer incremento del MVP)

- `POST /reportes`: reporte ciudadano sin cuenta (descripción, ubicación, video opcional).
- `GET /reportes/{codigo}`: estado del reporte con el código de seguimiento.
- `GET /cola`: cola priorizada (encabezado `X-Rol: veterinario` o `coordinador`).
- `POST /refugio/ingresos` y `GET /refugio/ocupacion`: cupos del refugio.

## Cómo ejecutarlo

```bash
python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest --cov=app                   # pruebas con cobertura
uvicorn app.api.main:app --reload  # documentación interactiva en http://127.0.0.1:8000/docs
```

## Flujo de trabajo

GitHub Flow: ramas cortas (`feature/`, `fix/`, `refactor/`, `chore/`, `docs/`) desde `main`,
integración por Pull Request con CI en verde y versiones etiquetadas según SemVer.
Ver `CHANGELOG.md` y `DEUDA_TECNICA.md`.
