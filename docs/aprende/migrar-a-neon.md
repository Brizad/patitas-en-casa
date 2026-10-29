# Migrar la base de Render a Neon (#154)

## Por qué

Render borra las bases gratis: **vencen 30 días después de creadas**, quedan 14 días de gracia
para pasarlas a un plan pagado y después **Render las elimina con todos sus datos**
(render.com/docs/free). Además no tienen respaldos.

**Neon** es PostgreSQL administrado con un plan gratis **permanente** («not a trial»), sin
tarjeta de crédito (neon.com/pricing, consultado el 29 de octubre de 2026):

| Plan gratis de Neon | Valor | ¿Alcanza para Patitas? |
|---|---|---|
| Almacenamiento | 1 GB por proyecto | Sí: la base de demostración pesa unos pocos MB |
| Cómputo | 100 CU-horas al mes por proyecto | Sí: se apaga sola tras 5 min sin uso y apagada no gasta |
| Despertar | La primera consulta después de dormir tarda un poco más | Igual que Render gratis |
| Historial | 6 horas para restaurar a un momento anterior | Es más de lo que da Render gratis (nada) |

La aplicación no cambia: es el mismo PostgreSQL. Lo único nuevo en el código es
`POSTGRES_SSLMODE` (Neon exige conexiones cifradas) y el script
`scripts/operacion/migrar_a_neon.py`, que copia y **verifica** tabla por tabla.

> Nada de esto lo ejecutó el asistente: necesita tus cuentas. El script se probó copiando
> entre dos bases locales (20 tablas, sin diferencias) y sus partes tienen pruebas
> (`tests/test_migrar_a_neon.py`).

## Qué cuenta crear y qué copiar

1. **Crea la cuenta** en https://neon.com → *Sign up* → «Continue with GitHub» (la misma
   cuenta `Brizad`; no pide tarjeta).
2. **Crea el proyecto**: nombre `patitas`, **Postgres 17** (el mismo que tienes en tu PC) y la
   región más cercana a la de Render. El servicio de Render está en **Oregon** (lo ves en
   Render → `patitas-en-casa` → *Settings* → *Region*); en Neon elige **AWS US West 2
   (Oregon)** si aparece, y si no, la de Estados Unidos más cercana. Base: `neondb` (la que
   crea Neon) está bien.
3. **Copia la dirección de Neon**: botón **Connect** → en la ventana «Connect to your
   branch» **apaga «Connection pooling»** (la dirección no debe tener `-pooler`) → copia la
   *connection string*. Se ve así (valores inventados):
   `postgresql://neondb_owner:CLAVE@ep-algo-123.us-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
4. **Copia la dirección de Render**: Render → base `patitas-bd` → página **Info** (o el menú
   **Connect** arriba a la derecha) → **External Database URL**.

Las dos direcciones tienen contraseña: **no las pegues en el chat, en un archivo del
repositorio ni en un commit.** Solo en la terminal cuando el script las pida y en Render.

## Paso a paso (unos 20 minutos)

### 1. Prepara tu PC (una vez)

En PowerShell, en la carpeta del proyecto (ya tienes PostgreSQL 17 instalado, que trae
`pg_dump` y `pg_restore`):

```bash
git checkout main
```
```bash
git pull
```
```bash
.venv\Scripts\activate
```

### 2. Detén la API mientras copias

Para que nadie cree un reporte durante la copia y se pierda: Render → `patitas-en-casa` →
*Settings* → **Suspend Web Service**. (Durante unos minutos el sitio no responde.)

### 3. Copia y verifica

```bash
python scripts/operacion/migrar_a_neon.py
```

Pega la *External Database URL* de Render y luego la *connection string* de Neon (con clic
derecho; no se ven al pegarlas). El script:

1. revisa que la base de Neon esté vacía (no pisa nada),
2. copia la de Render con `pg_dump` y la carga en Neon con `pg_restore` (la copia vive en una
   carpeta temporal que se borra al terminar),
3. cuenta las filas de **cada tabla** en las dos y dice si son iguales,
4. imprime las variables que debes poner en Render (sin la contraseña).

Si dice «La copia NO está completa», no sigas: copia el mensaje (no trae contraseñas) y
pídeme ayuda. Puedes repetir solo la comparación con `--verificar`.

### 4. Apunta Render a Neon

Render → `patitas-en-casa` → **Environment** → edita estas variables con lo que imprimió el
script, y agrega la contraseña de Neon:

| Variable | Valor |
|---|---|
| `POSTGRES_HOST` | `ep-…​.aws.neon.tech` (sin `-pooler`) |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_USER` | `neondb_owner` |
| `POSTGRES_PASSWORD` | la contraseña de la dirección de Neon |
| `POSTGRES_DB` | `neondb` |
| `POSTGRES_SSLMODE` | `require` (variable nueva) |

**Si Render no te deja editarlas** (aparecen «vinculadas» a `patitas-bd` porque vienen del
Blueprint), dímelo y preparo el PR que cambia `render.yaml`: las cinco `fromDatabase` pasan a
`sync: false` y se agrega `POSTGRES_SSLMODE`. No lo hice antes para no romper la conexión
actual mientras Neon no exista (ver `preguntas-para-brayan.md`, P-11).

### 5. Enciende y comprueba

1. *Settings* → **Resume Web Service**. Render redespliega; el arranque corre
   `alembic upgrade head`, que no cambia nada porque la copia ya trae la tabla
   `alembic_version`.
2. Abre https://patitas-en-casa-pnnk.onrender.com/app/ y consulta el código de un reporte que
   ya existía: si aparece, la API está leyendo de Neon.
3. Entra al panel con tu cuenta de administrador y mira la bitácora.

### 6. Después (cuando estés seguro)

- Deja la base de Render unos días sin usar como respaldo; luego bórrala tú (Render →
  `patitas-bd` → *Settings* → *Delete*), o deja que venza.
- El respaldo diario (RNF-15, P-07) sigue siendo una decisión tuya; Neon gratis guarda 6
  horas de historial, no un respaldo diario.

## Si algo sale mal

| Síntoma | Qué hacer |
|---|---|
| `No encuentro pg_dump` | Instala PostgreSQL 17 o agrega `C:\Program Files\PostgreSQL\17\bin` al PATH |
| `La base de Neon ya tiene tablas` | En Neon crea otra base vacía (*Databases* → *New*) o borra el proyecto y créalo de nuevo |
| `pg_restore falló: … version` | Tu `pg_restore` es más viejo que la base de Render: usa el de PostgreSQL 17 |
| La API no arranca tras el cambio | Vuelve a poner en Render las variables viejas (siguen en la base `patitas-bd`) y *Resume*: vuelves a estar como antes |
| `SSL connection is required` | Falta `POSTGRES_SSLMODE=require` en Render |

**Volver atrás es fácil mientras la base de Render exista:** sus datos no se tocan, el
script solo los lee.
