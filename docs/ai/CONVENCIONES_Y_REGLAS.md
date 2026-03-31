# CONVENCIONES_Y_REGLAS.md

## 1. Principio general

En este proyecto prima la compatibilidad y la precisión funcional por encima de la elegancia teórica.
Cada cambio debe respetar el flujo real del traductor y minimizar regresiones.

## 2. Convenciones de modificación

- Haz cambios pequeños y localizados.
- No reestructures el repositorio salvo necesidad clara.
- No cambies nombres de campos JSON existentes sin tocar también consumidores.
- No introduzcas dependencias nuevas si no son imprescindibles.
- No mezcles refactor estético con cambios funcionales en la misma propuesta.

## 3. Convenciones del motor Python

- Mantener estable el flujo `detectar proveedor → parser → normalización → matching → JSON`.
- Si añades un proveedor nuevo, usa el patrón ya existente en `PROVIDERS`.
- Si dos proveedores comparten layout, reutiliza parser mediante `fmt` común antes de crear uno nuevo.
- Si modificas regex, intenta que sean legibles y mantenibles.
- No reduzcas el umbral de fuzzy matching sin justificar impacto en falsos positivos.
- Cuando una línea no sea fiable, es preferible dejar `sin_match` antes que asignar un artículo incorrecto.

## 4. Convenciones del matching

El matching debe ser trazable.
Siempre que se pueda, conserva o mejora estos elementos:
- `match_status`
- `match_method`
- origen del aprendizaje

Los matches automáticos deben ser suficientemente seguros antes de persistir sinónimos.

## 5. Convenciones de persistencia

### Sinónimos
- El formato de clave no debe cambiarse sin migración.
- Los campos mínimos de cada entrada deben mantenerse.
- `manual-web` debe seguir diferenciándose de otros orígenes si se conserva la edición desde web.

### Historial
- Mantener formato simple y fácil de leer en JSON.
- No romper la compatibilidad con la tabla de historial de la web.

## 6. Convenciones de la capa web

- `api.php` es una capa puente, no una segunda lógica de negocio compleja.
- La web debe seguir esperando JSON limpio desde Python.
- Si se amplía la respuesta, debe hacerse de forma backward compatible.
- Validación mínima de archivo: tipo, tamaño, subida correcta.

## 7. Convenciones del entorno local

- Asumir Windows local.
- Asumir que la ruta de Python puede ser absoluta.
- No proponer rutas Linux por defecto.
- No asumir despliegues cloud si no se piden.

## 8. Cómo responder a tareas técnicas

Si la tarea es concreta, devolver preferentemente:
- solo el bloque modificado
- o una función completa
- o un diff

Si la tarea es ambigua, pedir solo lo mínimo:
- archivo exacto
- comportamiento actual
- comportamiento esperado
- restricción de compatibilidad

## 9. Qué revisar antes de dar una solución

Antes de proponer cambios, comprobar mentalmente:
- qué archivo inicia el flujo
- qué archivo consume la salida
- si se rompe el JSON
- si se invalida el historial o sinónimos previos
- si afecta a más de un proveedor
- si el cambio es de parser, matching o UI

## 10. Definición de “cambio seguro” en este repo

Un cambio se considera seguro si:
- mantiene el contrato actual
- toca el menor número posible de archivos
- no rompe parsers ya soportados
- no fuerza migraciones innecesarias
- no empeora precisión del matching
