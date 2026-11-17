# Documentación para el trabajo de grado

| Documento | Qué tiene | Cómo se mantiene |
|-----------|-----------|------------------|
| `c4.md` | Arquitectura en el modelo C4: contexto, contenedores y componentes (Mermaid) | A mano, verificado contra el código |
| `er.md` | Modelo entidad-relación (Mermaid) | Generado: `python -m scripts.tesis.generar_docs` |
| `diccionario-datos.md` | Cada tabla y columna con tipo, nulos, claves y restricciones | Generado |
| `catalogo-endpoints.md` | Todas las rutas con rol, códigos de respuesta y requisito | Generado |
| `pruebas.md` | Plan de pruebas y reporte con los números del CI | A mano, con los números del último CI de `main` |
| `trazabilidad.md` | Matriz RF/RNF → código → prueba → PR | A mano, al cerrar cada cambio |
| `triaje-ia.md` | Triaje con IA: cómo se entrenó (datos sintéticos), qué se midió, límites y cómo validar y reentrenar con reportes reales | A mano; los números salen de `scripts/ia/` |
| `guia-estilo.md` | Paleta con contrastes medidos, tipografía, espacios, componentes, correos, ilustraciones, accesibilidad y antes/después | A mano, con los valores de `app/diseno/sistema.css` |

Los generados no se editan a mano: si cambia el esquema o una ruta, se vuelve a correr el script
(una prueba, `tests/test_docs_tesis.py`, comprueba que no deja nada por fuera).
Otros documentos útiles: `docs/aprende/auditoria.md` (seguridad), `docs/aprende/e2e.md`
(pruebas de punta a punta), `docs/aprende/sustentacion.md` (preguntas del jurado).
