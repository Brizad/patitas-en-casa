# Fase 3 · Adopción

Issue #85. PR apilados: #86 → #87 → #88 → #89 → #90 → #91 → #92 → #93 → este. Se revisaron por separado y se integraron a `main` juntos en el **#108**.

## Qué hace

| Requisito | Qué se construyó |
|-----------|------------------|
| RF-08 | Cuenta propia del adoptante (`POST /adoptantes`, pública) con autorización de datos (Ley 1581) y su perfil. |
| RF-25 | El coordinador publica un animal de su refugio; catálogo público `GET /adopciones/animales`. |
| RF-27 | El adoptante solicita; el coordinador aprueba o rechaza con razón. |
| RN-05 | Restricciones duras: niños, otros animales y patio (`app/adopciones/reglas.py`). |
| RN-10 | Solo solicita quien llenó el perfil y aceptó el seguimiento. |
| RN-11 | Una sola adopción aprobada por animal (índice único parcial). |
| RF-10 | Seguimientos a los 30, 90 y 180 días, programados al aprobar y registrados con nota. |
| RF-29 | Compromiso de adopción en PDF para imprimir y firmar. |

## Por qué se hizo así

1. **Datos mínimos (RNF-08, RNF-16).** El perfil pregunta lo que sirve para decidir:
   vivienda, patio, niños, otros animales, horas solo y experiencia. No pregunta edad,
   género, estrato, religión ni etnia: no ayudan a saber si el animal estará bien cuidado y
   usarlos para decidir sería discriminar. La fase 4 recomienda con estos mismos datos.
2. **Autorización explícita.** Sin `autoriza_datos: true` no se crea la cuenta: la Ley 1581
   de 2012 exige autorización para tratar datos personales.
3. **El registro público siempre crea un adoptante.** El rol no viene del formulario; así
   nadie se registra como veterinario por esta puerta.
4. **Aprobar es una sola transacción.** Aprobar la solicitud, rechazar las otras del mismo
   animal, marcar la publicación como adoptada, dar el egreso (liberar el cupo) y programar
   los seguimientos ocurre todo o nada. Si algo falla, nada queda a medias (por ejemplo, un
   animal «adoptado» que sigue ocupando un cupo).
5. **RN-11 en la base.** El índice `uq_solicitudes_aprobada` (único y parcial: solo filas
   con `estado = 'aprobada'`) hace que, aunque dos coordinadores aprueben al mismo tiempo, la
   segunda transacción falle y no cambie nada.
6. **La restricción dura gana al puntaje.** Si el animal no puede vivir con niños y en la
   casa hay niños, no se aprueba, aunque todo lo demás encaje.
7. **PDF sin librerías.** Un PDF de texto se escribe en ~70 líneas (`app/documentos/pdf.py`).
   Así no se agregan varios MB a una imagen que debe caber en 512 MB de RAM.
8. **404 en vez de 403 para lo ajeno.** Si un adoptante pide el compromiso de otro, recibe
   «no encontrado»: no se confirma que esa solicitud existe.

## Recorrido de una petición: aprobar una adopción

1. En el panel, el coordinador pulsa «Aprobar» (`AdopcionesCoordinador.tsx`).
2. `decidir()` envía `POST /refugio/solicitudes/3/decision` con `{"aprobar": true}`.
3. `decidir_solicitud` (`app/api/main.py`) comprueba que el animal es de su refugio (si no,
   404) y llama a `ServicioAdopciones.decidir`.
4. El servicio comprueba que siga pendiente, lee el perfil y la publicación y aplica
   `restricciones_duras` (RN-05). Si hay motivos, lanza `RestriccionDura` → 409 con el texto.
5. Arma el plan de seguimientos (hoy + 30, 90 y 180 días) y llama a
   `RepositorioAdopcionesPostgres.aprobar`, que en una transacción ejecuta los `UPDATE` y los
   `INSERT` descritos arriba. Si el índice de RN-11 salta, la transacción se deshace y el
   servicio responde «ya tiene una adopción aprobada».
6. La respuesta trae el estado y las fechas de seguimiento; el panel las muestra.

## Archivos a leer, en orden

1. `app/adopciones/modelos.py`, `reglas.py`, `servicio.py`.
2. `app/adopciones/repositorio.py` (memoria) y `repositorio_postgres.py` (el método `aprobar`).
3. Migraciones `0016` a `0019`.
4. `app/documentos/pdf.py` y `app/adopciones/compromiso.py`.
5. En `app/api/main.py`, las rutas `/adoptantes`, `/adopciones/...` y `/refugio/solicitudes`.
6. Pruebas: `test_adoptante_perfil.py`, `test_publicacion.py`, `test_solicitudes.py`,
   `test_decision_adopcion.py`, `test_seguimientos.py`, `test_compromiso_pdf.py`.
7. Panel: `RegistroAdoptante.tsx`, `Adoptante.tsx`, `AdopcionesCoordinador.tsx`.

## Cómo probarlo

```bash
alembic upgrade head        # migraciones 0016 a 0019
pytest tests/test_decision_adopcion.py -q
```

A mano: como coordinador ingresa y publica un animal; en el inicio del panel pulsa
«¿Quieres adoptar? Crea tu cuenta», llena el perfil (acepta el seguimiento) y pide la
adopción; como coordinador apruébala; como adoptante descarga el compromiso en PDF.

## Preguntas de práctica para la sustentación

1. ¿Qué pasaría si aprobar no fuera una sola transacción y el servidor se cayera justo
   después de aprobar y antes del egreso?
2. ¿Cómo impide la base de datos que un animal tenga dos adopciones aprobadas?
3. ¿Por qué el perfil no pregunta la edad ni el estrato del adoptante?
4. ¿Por qué el registro público no deja elegir el rol?
5. ¿Por qué se escribió el PDF a mano en vez de usar una librería?

### Respuestas

<details><summary>Respuesta 1</summary>

Podría quedar una solicitud aprobada con el animal todavía ocupando un cupo y sin seguimientos, o la publicación «disponible» para otros. Al ser una transacción, si algo falla PostgreSQL deshace todo y el sistema queda como antes.

</details>

<details><summary>Respuesta 2</summary>

Con el índice único parcial `uq_solicitudes_aprobada` sobre `animal_id`, que solo cuenta las filas con `estado = 'aprobada'`. Una segunda aprobación del mismo animal viola el índice, la transacción falla y no cambia nada (RN-11).

</details>

<details><summary>Respuesta 3</summary>

Porque no sirve para saber si el animal estará bien cuidado y usarlo sería discriminar (RNF-16). Además, pedir menos datos personales es menos riesgo (Ley 1581, RNF-08): el perfil solo describe el hogar.

</details>

<details><summary>Respuesta 4</summary>

Porque si el rol viniera del formulario, cualquiera podría registrarse como veterinario o administrador. `POST /adoptantes` siempre crea el rol adoptante; las cuentas del personal solo las crea el administrador.

</details>

<details><summary>Respuesta 5</summary>

Porque una librería como ReportLab pesa varios MB y el servidor gratis tiene 512 MB de RAM. Un PDF de solo texto son objetos numerados y una tabla `xref` con sus posiciones: se escribe en unas 70 líneas y se prueba que cada posición apunte a su objeto.

</details>
