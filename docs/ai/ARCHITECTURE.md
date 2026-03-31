# ARCHITECTURE.md — VeraBuy Traductor

## 1. Objetivo del sistema

VeraBuy Traductor convierte líneas de producto de facturas PDF de proveedores florales en referencias del catálogo interno de VeraBuy.

Hace cuatro cosas principales:
- Detecta el proveedor a partir del texto del PDF.
- Parsea las líneas según el formato del proveedor.
- Normaliza atributos de producto.
- Hace matching contra el catálogo de artículos VeraBuy y persiste aprendizaje en sinónimos.

## 2. Arquitectura de alto nivel

El repositorio está dividido en tres capas:

### A. Motor de negocio en Python
Archivo principal: `verabuy_trainer.py`

Responsabilidades:
- Registro de proveedores.
- Detección de proveedor por patrones textuales.
- Extracción de texto PDF.
- Dataclasses de cabecera y líneas de factura.
- Carga del catálogo de artículos desde SQL.
- Almacén de sinónimos.
- Motor de matching.
- Historial de procesamientos.
- Parsers específicos por formato de proveedor.
- Lógica de rescate para líneas no parseadas por el parser principal.

### B. Wrapper de ejecución para la web
Archivo: `procesar_pdf.py`

Responsabilidades:
- Recibir un path de PDF.
- Detectar proveedor.
- Seleccionar parser.
- Cargar SQL de artículos.
- Cargar JSON de sinónimos.
- Ejecutar matching.
- Devolver un JSON limpio a stdout para que lo consuma PHP.

### C. Capa web PHP + JS
Archivos clave:
- `web/config.php`
- `web/api.php`
- `web/index.php`
- `web/assets/app.js`
- `web/assets/style.css`

Responsabilidades:
- Subida del PDF.
- Validación básica del archivo.
- Ejecución del script Python.
- Pintado de resultados.
- Consulta de historial.
- Consulta de diccionario de sinónimos.
- Guardado manual de sinónimos desde la UI.

## 3. Flujo extremo a extremo

### Flujo principal de proceso
1. El usuario accede a `web/index.php`.
2. La UI permite subir un PDF por click o drag & drop.
3. `web/assets/app.js` hace `POST` a `api.php?action=process` con el archivo.
4. `web/api.php`:
   - valida método
   - valida que el archivo sea PDF
   - valida tamaño máximo
   - lo guarda temporalmente
   - ejecuta Python con `procesar_pdf.py`
5. `procesar_pdf.py`:
   - detecta el proveedor
   - localiza el parser según `fmt`
   - carga `articulos (3).sql`
   - carga `sinonimos_universal.json`
   - parsea cabecera y líneas
   - divide cajas mixtas si aplica
   - intenta rescatar líneas no capturadas
   - ejecuta matching
   - devuelve JSON final
6. `api.php` devuelve ese JSON directamente al frontend.
7. `app.js` renderiza cabecera, estadísticas y tabla de líneas.

### Flujo de consulta de historial
1. El usuario cambia a la pestaña Historial.
2. `app.js` llama a `api.php?action=history`.
3. PHP lee `historial_universal.json`, ordena por fecha descendente y devuelve la lista.

### Flujo de consulta de sinónimos
1. El usuario cambia a la pestaña Sinónimos.
2. `app.js` llama a `api.php?action=synonyms`.
3. PHP lee `sinonimos_universal.json` y devuelve una lista indexada.
4. El frontend permite filtro por texto y por origen.

### Flujo de guardado manual de sinónimo
1. El usuario resuelve un caso no matcheado.
2. `api.php?action=save_synonym` recibe JSON.
3. PHP actualiza `sinonimos_universal.json` con `origen = manual-web`.
4. Ese aprendizaje queda persistido para procesamientos futuros.

## 4. Componentes del motor Python

## 4.1 Registro de proveedores
`PROVIDERS` define:
- clave interna del proveedor
- `id`
- `name`
- `fmt`
- `patterns`

`detect_provider(path)`:
- extrae texto del PDF
- busca patrones de proveedor
- devuelve metadatos del proveedor y el texto completo

## 4.2 Extracción de texto PDF
El sistema intenta usar:
- `pdfplumber` si está disponible
- `pdftotext -layout` como fallback

## 4.3 Modelos de datos
### `InvoiceHeader`
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

### `InvoiceLine`
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

`InvoiceLine` también construye un nombre esperado tipo VeraBuy a partir de especie, origen, variedad, talla, unidades y grado.

## 4.4 Carga de artículos
`ArticulosLoader`:
- carga el catálogo desde `articulos (3).sql`
- indexa artículos por nombre
- separa estructuras por especie
- mantiene índices específicos para rosas EC y COL
- calcula sufijos/marcas frecuentes por proveedor para mejorar matching

## 4.5 Almacén de sinónimos
`SynonymStore`:
- lee y escribe `sinonimos_universal.json`
- usa una clave compuesta basada en `provider_id` y `line.match_key()`
- guarda:
  - `articulo_id`
  - `articulo_name`
  - `origen`
  - `provider_id`
  - `species`
  - `variety`
  - `size`
  - `stems_per_bunch`
  - `grade`

## 4.6 Matcher
`Matcher` resuelve una línea usando una estrategia progresiva. Prioridades observadas:
- sinónimo existente
- match con marca del proveedor
- match exacto por nombre esperado
- matching automático adicional del motor
- fuzzy con umbral alto
- si no encuentra, `sin_match`

La intención es aprender automáticamente cuando el match es suficientemente fiable.

## 4.7 Historial
`History` persiste por número de factura:
- nombre PDF
- proveedor
- total USD
- número de líneas
- líneas OK
- líneas sin match
- fecha de proceso

## 4.8 Parsers por formato
El sistema tiene parsers específicos por formato/proveedor. Entre los observables están:
- `CantizaParser`
- `AgrivaldaniParser`
- `BrissasParser`
- `AlegriaParser`
- `AlunaParser`
- `DaflorParser`
- `EqrParser`
- `BosqueParser`
- `ColibriParser`

Hay varios proveedores que comparten parser vía `fmt`.

## 4.9 Red de seguridad
Existe lógica adicional para rescatar líneas de producto que el parser no haya capturado inicialmente.
También existe tratamiento de cajas mixtas antes del matching final.

## 5. Capa web

## 5.1 `web/config.php`
Define:
- raíz del proyecto
- ruta al ejecutable de Python
- script procesador
- directorio de uploads
- archivos JSON
- tamaño máximo del PDF

## 5.2 `web/api.php`
Acciones soportadas observadas:
- `process`
- `synonyms`
- `history`
- `save_synonym`

Contrato principal:
- siempre responde JSON
- actúa como puente simple entre navegador y motor Python

## 5.3 `web/index.php`
UI con tres pestañas:
- Procesar Factura
- Historial
- Sinónimos

## 5.4 `web/assets/app.js`
Responsabilidades:
- navegación entre pestañas
- subida de PDF
- llamada al endpoint de proceso
- render de cabecera y estadísticas
- carga de historial
- carga de sinónimos
- filtros de sinónimos

## 6. Persistencia

## 6.1 Persistencia estructurada
No hay base de datos activa dentro del proyecto web para el flujo principal observado.
Se usa persistencia por archivos:
- SQL dump como catálogo fuente
- JSON para aprendizaje y tracking

## 6.2 Archivos persistentes clave
- `articulos (3).sql`
- `sinonimos_universal.json`
- `historial_universal.json`

## 7. Decisiones de diseño que conviene preservar

- Separación clara entre motor Python y UI web.
- Contrato JSON estable entre `procesar_pdf.py` y `web/api.php`.
- Aprendizaje incremental vía sinónimos persistidos.
- Parsers específicos por formato de factura.
- Matching conservador y trazable mediante `match_status` y `match_method`.

## 8. Riesgos si se modifica sin cuidado

- Romper el JSON devuelto por Python rompe el frontend.
- Cambiar la lógica de clave de sinónimo puede invalidar aprendizaje previo.
- Cambiar normalización sin migración puede duplicar o inutilizar sinónimos.
- Relajar demasiado el fuzzy puede generar falsos positivos peligrosos.
- Cambiar `fmt` o `patterns` de proveedores puede romper detección automática.

## 9. Recomendaciones para futuras mejoras

- Extraer configuración sensible a un archivo `.env` o similar si el proyecto crece.
- Añadir tests por parser con PDFs o textos de ejemplo.
- Añadir un modo debug opcional con trazas de matching por línea.
- Separar mejor capa dominio y utilidades si el motor sigue creciendo.
- Añadir validación/edición desde la web para resolver `sin_match` más rápido.
