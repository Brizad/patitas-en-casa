# Imagen de la API con el panel compilado (II-03, I1). Construir: docker compose build
# 1) Compilar el panel React
FROM node:22-alpine AS panel
WORKDIR /panel
COPY panel/package.json panel/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY panel/ ./
RUN npm run build -- --outDir /panel_web

# 2) API en Python
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini ./
COPY migraciones/ migraciones/
COPY app/ app/
COPY --from=panel /panel_web app/panel_web/
# Sin privilegios de administrador dentro del contenedor.
RUN useradd --create-home patitas
USER patitas
EXPOSE 8000
# Aplica las migraciones pendientes y arranca la API.
CMD ["sh", "-c", "alembic upgrade head && uvicorn --factory app.api.main:crear_app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
