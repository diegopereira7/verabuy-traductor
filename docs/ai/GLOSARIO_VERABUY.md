# GLOSARIO_VERABUY.md

## Términos del proyecto

### VeraBuy Traductor
Herramienta que transforma líneas de factura PDF de proveedores en artículos internos de VeraBuy.

### Artículo VeraBuy
Referencia interna destino a la que debe matchear cada línea de factura.
Normalmente tiene `articulo_id` y `articulo_name`.

### Proveedor
Emisor de la factura PDF.
El sistema lo detecta por patrones textuales en el propio PDF.

### `provider_id`
ID numérico del proveedor usado por el sistema de matching y por los sinónimos.

### `provider_key`
Clave interna corta del proveedor dentro del código Python.
Ejemplo: `cantiza`, `agrivaldani`, `colibri`.

### `fmt`
Formato/parser asignado a un proveedor.
Varios proveedores pueden compartir el mismo `fmt`.

### Parser
Bloque de lógica que entiende el layout de factura de un proveedor o familia de proveedores.
Su salida debe ser una cabecera y una lista de `InvoiceLine`.

### `InvoiceHeader`
Dataclass con la cabecera general de la factura.

### `InvoiceLine`
Dataclass con una línea de producto ya normalizada.

### Species / `species`
Especie normalizada del producto.
Valores observados:
- `ROSES`
- `CARNATIONS`
- `HYDRANGEAS`
- `ALSTROEMERIA`
- `GYPSOPHILA`
- `CHRYSANTHEMUM`
- `OTHER`

### Variety / `variety`
Variedad, color o descriptor comercial según la especie y el proveedor.

### Grade / `grade`
Calidad del producto.
Valores frecuentes:
- `FANCY`
- `SELECT`
- `PREMIUM`
- `STANDARD`

### Size / `size`
Talla o longitud en centímetros cuando aplica.

### SPB / `stems_per_bunch`
Stems per bunch. Número de tallos por ramo.

### `bunches`
Número de ramos en la línea.

### `stems`
Número total de tallos de la línea.

### `price_per_stem`
Precio unitario por tallo.

### `line_total`
Importe total de la línea.

### `box_type`
Tipo de caja o presentación observada en factura.
Puede ser importante para interpretar líneas mixtas o layouts concretos.

### `label`
Etiqueta auxiliar de la línea, a veces usada para distinguir cajas, lotes o marcas internas.

### `farm`
Finca o referencia del productor cuando aparece en factura.

### Matching
Proceso por el que una línea parseada se asigna a un artículo VeraBuy.

### `match_status`
Estado final del match.
Valores observables o esperables:
- `ok`
- `sin_match`
- `sin_parser`
- `pendiente`

### `match_method`
Método por el que se logró el match.
Ejemplos observables o derivados del código:
- `sinónimo`
- `marca`
- `exacto`
- `fuzzy ...`

### Sinónimo
Equivalencia persistida entre una combinación de atributos de línea de factura y un artículo VeraBuy.
Se guarda en `sinonimos_universal.json`.

### `origen`
Procedencia del sinónimo.
Valores observados o inferibles por código:
- `manual`
- `manual-web`
- `auto`
- `auto-fuzzy`
- `auto-marca`

### Historial
Registro persistido de facturas procesadas y su resultado.
Se guarda en `historial_universal.json`.

### `articulos (3).sql`
Dump SQL grande que contiene el catálogo de artículos VeraBuy usado como fuente de matching.

### Rescue / rescate
Lógica posterior al parser principal para intentar recuperar líneas de producto que el parser no capturó.

### Cajas mixtas / mixed boxes
Líneas o cajas que contienen mezcla de variedades o formatos y requieren un tratamiento previo antes del matching.

## Proveedores observados en el código

Listado parcial-alto valor para contexto:
- Cantiza Flores
- Valthomig
- Agrivaldani
- Luxus Blumen
- Brissas
- La Alegria Farm
- Olimpo Flowers
- Fairis Garden
- Inversiones del Neusa
- Daflor
- Turflor
- EQR USA
- Bosque Flowers
- Colibri Flowers
- Benchmark Growers
- Latin Flowers
- Multiflora
- Florsani
- Maxiflores
- Mystic Flowers
- Fiorentina Flowers
- Stampsybox
- Prestige Roses
- Rosely Flowers
- Condor Andino
- Starflowers (Malima)
- Monterosas Farms
- Secore Floral
- Tessa Corp
- Uma Flowers
- Valle Verde Farms
- Verdes La Estacion

## Qué debe entender Claude al leer este glosario

- Esto no es un OCR genérico ni un ETL genérico.
- Es una herramienta muy orientada a un dominio concreto: flor cortada, proveedores concretos y catálogo VeraBuy.
- El objetivo no es solo parsear texto, sino traducir a artículos internos correctos y aprender con el tiempo.
