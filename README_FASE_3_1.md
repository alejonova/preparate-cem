# Fase 3.1 — Correcciones del examen

Esta versión parte de la Fase 3 UGOS corregida y añade:

- Logout mediante POST, con redirección al login.
- Prevención de caché de páginas autenticadas después del logout.
- Durante el examen solo se muestra `Pregunta X de 40`; el número original del banco no se muestra.
- Las opciones A/B/C/D se mezclan de forma aleatoria al iniciar cada examen.
- El orden de las opciones permanece fijo durante ese intento.
- La respuesta correcta se recalcula según el orden mezclado, sin alterar el banco original.
- Se elimina el botón Anterior.
- Una vez enviada una respuesta y avanzada la posición, la pregunta anterior queda cerrada y no puede modificarse desde el servidor.
- En la última pregunta aparece `Finalizar examen`.

El banco, usuarios, resultados e historial permanecen en la base de datos existente. La actualización del código no requiere borrar `data/db.sqlite3`.
