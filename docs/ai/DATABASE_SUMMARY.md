# DATABASE_SUMMARY.md — VeraBuy Traductor

## 1. Qué datos usa realmente el proyecto

El proyecto no parece depender de una base de datos relacional activa en tiempo de ejecución para el flujo observado de traducción web.
En su lugar usa tres fuentes persistentes:

- `articulos (3).sql`
- `sinonimos_universal.json`
- `historial_universal.json`

## 2. `articulos (3).sql`

## 2.1 Rol funcional
Es el catálogo maestro de artículos VeraBuy contra el que el motor intenta matchear las líneas de factura.

## 2.2 Cómo lo consume el código
`ArticulosLoader.load_from_sql()`:
- abre el archivo SQL directamente como texto
- recorre línea a línea
- procesa líneas que empiezan por `(`, es decir, tuplas de un `INSERT`
- construye índices internos para acelerar matching

## 2.3 Índices observados en memoria
El cargador mantiene al menos estos índices:
- `articulos`: diccionario principal de artículos por ID
- `by_name`: índice por nombre exacto
- `rosas_ec`: índice específico para rosas Ecuador
- `rosas_col`: índice específico para rosas Colombia
- `by_species`: índice por especie normalizada
- `brand_by_provider`: sufijo o marca más frecuente por proveedor

## 2.4 Especies normalizadas observadas en el loader
Mapeo observado desde prefijos del artículo:
- `ROSA EC` → `ROSES_EC`
- `ROSA COL` → `ROSES_COL`
- `MINI CLAVEL` → `CARNATIONS`
- `CLAVEL` → `CARNATIONS`
- `HYDRANGEA` → `HYDRANGEAS`
- `ALSTROMERIA` / `ALSTROEMERIA` → `ALSTROEMERIA`
- `PANICULATA` → `GYPSOPHILA`
- `CRISANTEMO` → `CHRYSANTHEMUM`
- `DIANTHUS` → `OTHER`

## 2.5 Qué debes asumir al trabajar con este dump
- Es la fuente de verdad del catálogo VeraBuy.
- No debes cambiar su formato sin rehacer el loader.
- Si Claude necesita razonar sobre artículos concretos, conviene subir este SQL como conocimiento del proyecto.
- Si el objetivo es editar lógica de matching, el dump completo es mejor que un resumen corto.

## 3. `sinonimos_universal.json`

## 3.1 Rol funcional
Es la memoria incremental del traductor.
Guarda equivalencias ya aprendidas entre una línea de factura y un artículo VeraBuy.

## 3.2 Estructura observable por código
La clave es compuesta y se construye así:
- `provider_id|line.match_key()`

Cada valor contiene al menos:
- `articulo_id`
- `articulo_name`
- `origen`
- `provider_id`
- `species`
- `variety`
- `size`
- `stems_per_bunch`
- `grade`

## 3.3 Orígenes observados
Valores de `origen` observables o deducibles por código:
- `manual`
- `auto`
- `auto-fuzzy`
- `manual-web`
- `auto-marca`

## 3.4 Uso en runtime
- El motor consulta primero este JSON antes de buscar por catálogo.
- Cuando hay un match automático fiable, puede persistir nuevo aprendizaje.
- La web también puede guardar sinónimos manuales.

## 4. `historial_universal.json`

## 4.1 Rol funcional
Registra las facturas ya procesadas y resume el resultado.

## 4.2 Estructura observable por código
Se guarda por clave de factura y cada entrada contiene al menos:
- `pdf`
- `provider`
- `total_usd`
- `lineas`
- `ok`
- `sin_match`
- `fecha`

## 4.3 Uso en runtime
- La web lo consulta para mostrar historial.
- El motor lo actualiza al terminar procesamientos.

## 5. Entidades de negocio relevantes

## 5.1 `InvoiceHeader`
Campos observados:
- `invoice_number`
- `date`
- `awb`
- `hawb`
- `provider_key`
- `provider_id`
- `provider_name`
- `total`
- `airline`
- `incoterm`

## 5.2 `InvoiceLine`
Campos observados:
- `raw_description`
- `species`
- `variety`
- `grade`
- `origin`
- `size`
- `stems_per_bunch`
- `bunches`
- `stems`
- `price_per_stem`
- `price_per_bunch`
- `line_total`
- `label`
- `farm`
- `box_type`
- `provider_key`
- `articulo_id`
- `articulo_name`
- `match_status`
- `match_method`

## 6. Qué conviene subir a Claude como conocimiento

Imprescindible:
- `articulos (3).sql`
- `sinonimos_universal.json`
- este resumen

Muy recomendable:
- `historial_universal.json`

Opcional según tarea:
- PDFs de ejemplo
- recortes de líneas conflictivas

## 7. Qué no asumir sin verificar

- El nombre exacto de la tabla SQL del dump no se ha verificado por lectura completa del archivo.
- La posición exacta de cada columna del SQL no se debe inventar.
- Si una tarea depende de columnas concretas del dump, conviene dar a Claude el fragmento SQL exacto o subir el archivo completo.
