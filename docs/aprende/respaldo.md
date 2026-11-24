# Respaldo diario de la base (RNF-15)

**Qué hace** el flujo `.github/workflows/respaldo.yml`, cada día a las 02:17 (hora de Colombia)
y cuando lo lances a mano:

1. Revisa los secretos. Si falta alguno, deja un aviso amarillo y termina **sin fallar**.
2. Saca una copia de la base de Neon con `pg_dump` (formato personalizado).
3. La cifra con AES-256 (`openssl`, clave derivada con PBKDF2) y borra la copia sin cifrar.
4. **Prueba que sirve**: la descifra, la restaura en una base PostgreSQL temporal dentro del
   mismo flujo y compara el número de tablas y la revisión de Alembic. Si no restaura, el flujo
   falla y lo ves en rojo.
5. Guarda el archivo cifrado como artefacto de la ejecución durante **14 días**.

Además (`scripts/operacion/vigilar_respaldo.py`, con pruebas):

- **Antes de copiar** pregunta la versión al servidor (`SHOW server_version_num`). Si Neon
  corre una versión mayor que la de `pg_dump`, el flujo se detiene y dice qué línea cambiar:
  `PG_VERSION: "18"` por la nueva (lo que pasó en #210).
- **Alerta de respaldo viejo:** después de cada respaldo, y otra vez a las 08:17, revisa los
  artefactos guardados. Si el respaldo más reciente tiene **más de 26 horas** (o no hay
  ninguno) el flujo queda **en rojo** y GitHub te avisa por correo. Para revisarlo a mano sin
  tocar Neon: *Run workflow* con la casilla «Solo revisar la edad del último respaldo».

Con eso: RPO ≤ 24 h (la copia más vieja posible tiene un día) y RTO ≤ 4 h (restaurar son unos
minutos, ver abajo).

## Qué secretos crear en GitHub

Repositorio → *Settings* → *Secrets and variables* → *Actions* → *New repository secret*:

| Secreto | Valor |
|---------|-------|
| `NEON_DATABASE_URL` | Cadena de conexión de Neon (*Connect* → *Connection string*), con `?sslmode=require`. Usa el rol de **solo lectura** si lo tienes. |
| `RESPALDO_CLAVE` | Una frase larga y aleatoria (32 caracteres o más). **Guárdala en tu gestor de contraseñas:** sin ella los respaldos no se pueden abrir. |

Nunca los pegues en el chat, en issues ni en el repositorio. Si la versión de Neon es otra que
la 18, cambia `PG_VERSION` en el flujo (el cliente debe ser igual o más nuevo que el servidor).

Para probarlo ya: *Actions* → *Respaldo diario* → *Run workflow*.

## Cómo restaurar

1. *Actions* → ejecución del respaldo → *Artifacts* → descarga `respaldo-…` y descomprime el zip.
2. Verifica el archivo (opcional): `sha256sum -c patitas.dump.enc.sha256`.
3. Descifra (te pide la clave por una variable, no queda en el historial de comandos):

   ```bash
   export RESPALDO_CLAVE='tu-clave'
   openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:RESPALDO_CLAVE \
     -in patitas.dump.enc -out patitas.dump
   ```

4. Restaura en una base **vacía** (nueva rama o proyecto de Neon, o una local):

   ```bash
   createdb -h localhost -U postgres patitas_restaurada
   pg_restore -h localhost -U postgres -d patitas_restaurada --no-owner patitas.dump
   ```

   Contra Neon: `pg_restore -d "<cadena de conexión de la base vacía>" --no-owner patitas.dump`.
5. Apunta `POSTGRES_HOST`, `POSTGRES_DB`… en Render a la base restaurada y reinicia la API.

## Restaurar en una base nueva de Neon (flujo automático, #394)

Sirve cuando la base de producción no está disponible (por ejemplo, suspendida por el límite de
horas) y hay que montar otra con el último respaldo bueno. El flujo
`.github/workflows/restaurar-a-neon-nuevo.yml` hace los pasos de arriba en GitHub:

1. Elige el artefacto `respaldo-…` más reciente que no venció (solo existe si ese respaldo pasó
   la copia, el cifrado y la prueba de restauración) o la ejecución que le indiques.
2. Lo descarga, comprueba el `sha256` y lo descifra con `RESPALDO_CLAVE`.
3. **Se niega** si la base destino ya tiene tablas (nunca restaura encima de datos).
4. Hace `pg_restore --no-owner --no-privileges --exit-on-error` con `postgres:18`.
5. Comprueba que hay tantas tablas como en la copia y muestra `alembic_version`.

La cadena de conexión nunca se imprime; si algo falla, el nombre del servidor sale tapado.

**Cómo lanzarlo:**

1. En Neon, crea un proyecto (o base) **nuevo y vacío**, versión 18. Copia su *Connection
   string* **directa** (sin `-pooler` en el host) con `?sslmode=require`.
2. GitHub → *Settings* → *Secrets and variables* → *Actions* → *New repository secret*:
   `NEON_DATABASE_URL_NUEVA` = esa cadena.
3. *Actions* → *Restaurar en Neon nuevo* → *Run workflow* → en «confirmar» escribe `RESTAURAR`
   (y deja vacío el id de la ejecución para usar el último respaldo bueno).
   Desde la terminal: `gh workflow run restaurar-a-neon-nuevo.yml -f confirmar=RESTAURAR`.
4. Al terminar en verde, el resumen dice las tablas y la `alembic_version`. Luego apunta Render
   a la base nueva (`POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) y
   cambia también el secreto `NEON_DATABASE_URL` del respaldo diario por la cadena nueva.

Si falta el secreto, el flujo falla en el primer paso con «Falta el secreto
NEON_DATABASE_URL_NUEVA».

## Límites que debes saber

- Los artefactos viven 14 días; para guardar uno más tiempo, descárgalo.
- La copia incluye datos personales (contactos y perfiles ya vienen cifrados con
  `PATITAS_CLAVE_DATOS`, pero también hay correos y descripciones): por eso el archivo va
  cifrado: en un repositorio público cualquiera con sesión de GitHub puede descargar los
  artefactos, y solo la clave `RESPALDO_CLAVE` los protege.
- Si pierdes `PATITAS_CLAVE_DATOS`, la copia restaura pero esos campos no se pueden leer.
