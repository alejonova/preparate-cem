# Administración — rediseño visual y gestión de bancos

Esta versión mantiene Django Admin como motor administrativo, pero incorpora una interfaz visual personalizada y funciones adicionales para la gestión de la plataforma.

## Funciones

- Gestión de usuarios: búsqueda, filtros, activación y deshabilitación.
- Creación y edición de materias.
- Creación y edición individual de preguntas.
- Importación de bancos de preguntas en JSON o CSV.
- La importación crea preguntas nuevas y, por defecto, actualiza las existentes cuando coinciden materia + número.
- Los resultados de exámenes no se muestran en el administrador en esta versión.

## Formato JSON

El JSON debe ser una lista de objetos con estas claves:

- `number`
- `text`
- `option_a`
- `option_b`
- `option_c`
- `option_d`
- `correct_option`

`correct_option` debe ser `A`, `B`, `C` o `D`.

## Formato CSV

La primera fila debe contener exactamente estas columnas:

`number,text,option_a,option_b,option_c,option_d,correct_option`

## Importación

Desde **Administración → Preguntas → Importar banco** se selecciona la materia y el archivo. La operación se realiza dentro de una transacción para evitar importaciones parciales.
