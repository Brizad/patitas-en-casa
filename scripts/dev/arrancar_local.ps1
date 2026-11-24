<#
.SYNOPSIS
  Arranca Patitas en Casa en este PC con Windows (PostgreSQL 17 local), con datos de demostración.

.DESCRIPTION
  1. Verifica que exista .env (si no, dice qué copiar de .env.example).
  2. Carga sus variables en esta ventana (no imprime ningún valor).
  3. Prepara Python (.venv) si hace falta.
  4. Aplica las migraciones: alembic upgrade head.
  5. Compila el panel: npm ci y npm run build en panel/ (queda en app/panel_web).
  6. Activa los datos de demostración (PATITAS_DEMO_ACTIVA=true).
  7. Arranca uvicorn --factory app.api.main:crear_app --reload --port 8000.
  Guía: docs/aprende/desarrollo-local.md

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\dev\arrancar_local.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\dev\arrancar_local.ps1 -SinPanel
#>
param(
  [string]$ArchivoEnv = ".env",   # otro archivo solo para probar con otra base
  [int]$Puerto = 8000,
  [switch]$SinPanel,              # no recompilar el panel (más rápido si no cambió)
  [switch]$SinRecarga             # sin --reload (por ejemplo, para pruebas con Playwright)
)

$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $raiz

function Escribir-Paso([string]$texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Detener([string]$texto) { Write-Host "`n$texto" -ForegroundColor Red; exit 1 }
function Exigir-Exito([string]$que) {
  if ($LASTEXITCODE -ne 0) { Detener "Falló: $que (código $LASTEXITCODE). Lee el mensaje de arriba." }
}

# 1. El archivo de entorno -------------------------------------------------------------------
Escribir-Paso "1/6 Revisando $ArchivoEnv"
if (-not (Test-Path $ArchivoEnv)) {
  Detener @"
No existe $ArchivoEnv. Créalo a partir del ejemplo:

    Copy-Item .env.example .env
    notepad .env

y completa como mínimo:
  POSTGRES_PASSWORD        la contraseña de tu usuario postgres local
  POSTGRES_DB              patitas
  PATITAS_JWT_SECRETO      genera una con:  python -c "import secrets; print(secrets.token_hex(32))"
  PATITAS_DEMO_CONTRASENA  12 caracteres o más: la de las cuentas *@demo.patitas.co
"@
}

# 2. Cargar sus variables en esta ventana (sin mostrar valores) ----------------------------
foreach ($linea in Get-Content -Path $ArchivoEnv -Encoding UTF8) {
  if ($linea -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
    $nombre = $Matches[1]
    $valor = $Matches[2].Trim().Trim('"').Trim("'")
    if ($valor -ne "" -and -not [Environment]::GetEnvironmentVariable($nombre, "Process")) {
      [Environment]::SetEnvironmentVariable($nombre, $valor, "Process")
    }
  }
}
$faltan = @("POSTGRES_PASSWORD", "PATITAS_JWT_SECRETO", "PATITAS_DEMO_CONTRASENA") |
  Where-Object { -not [Environment]::GetEnvironmentVariable($_, "Process") }
if ($faltan) { Detener "Faltan en ${ArchivoEnv}: $($faltan -join ', '). Complétalas y vuelve a correr el script." }
if ($env:PATITAS_DEMO_CONTRASENA.Length -lt 12) {
  Detener "PATITAS_DEMO_CONTRASENA debe tener 12 caracteres o más."
}
if (-not $env:POSTGRES_DB) { $env:POSTGRES_DB = "patitas" }
Write-Host "Base: $($env:POSTGRES_DB) en $($env:POSTGRES_HOST):$($env:POSTGRES_PORT) (usuario $($env:POSTGRES_USER))"

# 3. Python ----------------------------------------------------------------------------------
Escribir-Paso "2/6 Preparando Python"
$python = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  Write-Host "No hay .venv: lo creo e instalo las dependencias (unos minutos, solo la primera vez)."
  py -3.12 -m venv .venv; Exigir-Exito "crear .venv (¿está instalado Python 3.12?)"
  & $python -m pip install -q -r requirements-dev.txt; Exigir-Exito "pip install"
}
& $python -c "import fastapi, uvicorn, alembic" 2>$null
if ($LASTEXITCODE -ne 0) {
  & $python -m pip install -q -r requirements-dev.txt; Exigir-Exito "pip install"
}

# 4. Migraciones -----------------------------------------------------------------------------
Escribir-Paso "3/6 Migraciones (alembic upgrade head)"
& $python -m alembic upgrade head
Exigir-Exito "alembic upgrade head (¿PostgreSQL está encendido y existe la base $($env:POSTGRES_DB)?)"

# 5. Panel -----------------------------------------------------------------------------------
if ($SinPanel) {
  Escribir-Paso "4/6 Panel: se usa el ya compilado (-SinPanel)"
  if (-not (Test-Path "app\panel_web\index.html")) { Detener "No hay panel compilado: corre sin -SinPanel." }
} else {
  Escribir-Paso "4/6 Compilando el panel (npm ci y npm run build)"
  Push-Location panel
  try {
    npm ci --no-audit --no-fund; Exigir-Exito "npm ci (¿está instalado Node.js 22 o más nuevo?)"
    npm run build; Exigir-Exito "npm run build"
  } finally { Pop-Location }
}

# 6. Datos de demostración y arranque ----------------------------------------------------------
Escribir-Paso "5/6 Datos de demostración activados (PATITAS_DEMO_ACTIVA=true)"
$env:PATITAS_DEMO_ACTIVA = "true"

Escribir-Paso "6/6 Arrancando la API en http://localhost:$Puerto"
Write-Host @"
  Inicio:            http://localhost:$Puerto/
  PWA (ciudadano):   http://localhost:$Puerto/app/
  Panel (personal):  http://localhost:$Puerto/panel/
  API (Swagger):     http://localhost:$Puerto/docs
  Cuentas: admin, veterinaria, coordinador, rescatista, adoptante y alcaldia @demo.patitas.co
  con la contraseña PATITAS_DEMO_CONTRASENA de tu .env. Ctrl+C para detener.
"@
$argumentos = @("-m", "uvicorn", "--factory", "app.api.main:crear_app", "--port", "$Puerto")
if (-not $SinRecarga) { $argumentos += "--reload" }
& $python @argumentos
