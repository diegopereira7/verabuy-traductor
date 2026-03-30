# PROMPT REUTILIZABLE PARA CLAUDE CODE — Analizar Facturas Problemáticas y Mejorar el Proyecto

> **Cómo usar este prompt:** Cada vez que tengas facturas que fallaron o dieron resultados malos, copia este prompt en Claude Code junto con los PDFs problemáticos. Claude Code analizará los PDFs, diagnosticará qué falló, y modificará el código del proyecto para que funcionen la próxima vez.
>
> **Preparación:** Copia los PDFs problemáticos a una carpeta dentro del proyecto, por ejemplo `pendientes/`. Luego pega este prompt.

---

## Tu tarea

En la carpeta `pendientes/` (o la carpeta que te indique el usuario) hay facturas PDF que el traductor no pudo procesar correctamente. Tu trabajo es:

1. Analizar cada PDF para entender qué falló
2. Diagnosticar la causa raíz (proveedor sin parser, parser con bugs, sinónimos faltantes)
3. Corregir el proyecto para que estas facturas funcionen la próxima vez SIN necesidad de IA

Al terminar, el usuario debe poder ejecutar el traductor normalmente sobre estas facturas y obtener resultados correctos.

---

## Paso 1 — Entender el proyecto (ejecutar siempre, aunque ya lo hayas hecho antes)

```bash
# Estructura del proyecto
find . -type f \( -name "*.py" -o -name "*.php" -o -name "*.js" -o -name "*.json" \) | grep -v node_modules | grep -v __pycache__ | sort

# Proveedores registrados
cat config.py

# Parsers disponibles
cat parsers/__init__.py

# Detección de proveedores
cat pdf.py

# Modelos de datos (InvoiceHeader, InvoiceLine)
grep -rn "class Invoice" src/*.py *.py 2>/dev/null

# Sinónimos actuales (resumen)
cat sinonimos_universal.json | python -c "
import sys, json
d = json.load(sys.stdin)
print(f'Total sinónimos: {len(d)}')
" 2>/dev/null

# Post-procesamiento (matching, sinónimos)
cat procesar_pdf.py
```

---

## Paso 2 — Analizar cada PDF problemático

Para CADA PDF en la carpeta de pendientes:

```bash
# Listar los PDFs pendientes
ls -la pendientes/*.pdf 2>/dev/null || ls -la *.pdf 2>/dev/null

# Para cada PDF, extraer el texto completo
python -c "
import pdfplumber, sys
with pdfplumber.open(sys.argv[1]) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ''
        print(f'=== PÁGINA {i+1} ===')
        print(text)
        print()
        # Intentar extraer tablas
        tables = page.extract_tables()
        if tables:
            for j, table in enumerate(tables):
                print(f'--- TABLA {j+1} ---')
                for row in table:
                    print(row)
                print()
" pendientes/NOMBRE_DEL_PDF.pdf
```

**Ejecutar esto para CADA PDF.** Después, para cada uno:

```bash
# Intentar procesarlo con el sistema actual para ver el error exacto
python procesar_pdf.py pendientes/NOMBRE_DEL_PDF.pdf
```

---

## Paso 3 — Diagnosticar y clasificar cada factura

Después de analizar todos los PDFs, clasificar cada uno en una de estas categorías:

### Categoría A — Proveedor sin parser

**Síntoma:** El sistema devuelve `"Proveedor no reconocido"` o `"Sin parser para formato X"`.

**Qué hacer:**

1. Leer los parsers existentes de proveedores SIMILARES (mismo tipo de producto, estructura de PDF parecida):
   ```bash
   # Leer 3-4 parsers existentes como referencia de estilo y patrones
   cat parsers/cantiza.py
   cat parsers/golden.py
   cat parsers/otros.py
   ```

2. Analizar el PDF del proveedor nuevo:
   - ¿Tiene tablas estructuradas (pdfplumber.extract_table funciona)?
   - ¿O es texto plano que hay que parsear con regex?
   - ¿Dónde está la descripción del producto, los tallos, el precio, el color?
   - ¿Qué keywords identifican a este proveedor? (nombre de empresa, dirección, nº de factura)

3. Crear el parser nuevo:
   - Crear archivo `parsers/nombre_proveedor.py` siguiendo EXACTAMENTE el patrón de los parsers existentes
   - Misma interfaz: clase con método `parse(text, pdata)` que retorna `(InvoiceHeader, list[InvoiceLine])`
   - Mismos imports y tipos que los parsers existentes
   - Regex y lógica específica para el formato de este proveedor
   - Incluir docstring con ejemplo del formato

4. Registrar el proveedor:
   - Añadir entrada en `PROVIDERS` en `config.py` con `patterns` (keywords) y `fmt`
   - Añadir entrada en `FORMAT_PARSERS` en `parsers/__init__.py`

5. Verificar:
   ```bash
   python procesar_pdf.py pendientes/NOMBRE_DEL_PDF.pdf
   ```
   Debe devolver resultados válidos con `"ok": true`.

### Categoría B — Parser existe pero da resultados malos

**Síntoma:** El sistema devuelve `"ok": true` pero los datos son incorrectos, incompletos, o tienen campos mezclados.

**Qué hacer:**

1. Identificar qué parser se usó:
   ```bash
   python -c "
   from pdf import detect_provider
   import pdfplumber
   with pdfplumber.open('pendientes/NOMBRE_DEL_PDF.pdf') as pdf:
       text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
   p = detect_provider(text)
   print(f'Proveedor: {p}')
   "
   ```

2. Leer el parser actual:
   ```bash
   cat parsers/NOMBRE_DEL_PARSER.py
   ```

3. Comparar el output actual vs lo que debería ser:
   - Ejecutar el parser y ver qué extrae
   - Comparar manualmente con el contenido real del PDF
   - Identificar dónde falla: ¿regex incorrecta? ¿columnas cambiadas? ¿formato de fecha? ¿nuevo campo?

4. **Diagnosticar la causa raíz.** Las causas más comunes son:
   - **El proveedor cambió el formato:** nuevas columnas, orden diferente, campos renombrados. Ajustar regex/índices.
   - **Caso edge no contemplado:** productos con caracteres especiales, líneas con más/menos campos de lo esperado, cajas mixtas con formato diferente. Añadir manejo del caso edge.
   - **Regex demasiado específica:** solo captura un patrón pero el proveedor tiene variaciones. Hacer la regex más flexible.
   - **Regex demasiado amplia:** captura datos incorrectos. Hacerla más precisa.
   - **Campo numérico parseado como texto** o viceversa. Ajustar conversión de tipos.

5. Corregir el parser:
   - Modificar el archivo del parser existente
   - NO crear un parser nuevo (es el mismo proveedor, solo hay que corregir el que existe)
   - Añadir comentario explicando la corrección: `# FIX: el formato cambió en 2025, columna X ahora es Y`
   - Si el cambio es grande, preservar la lógica anterior comentada por si hay que revertir

6. Verificar con el PDF problemático Y con un PDF anterior del mismo proveedor:
   ```bash
   # El PDF problemático ahora funciona
   python procesar_pdf.py pendientes/NOMBRE_DEL_PDF_NUEVO.pdf
   
   # Un PDF anterior del mismo proveedor sigue funcionando (no regresión)
   python procesar_pdf.py facturas_anteriores/NOMBRE_DEL_PDF_VIEJO.pdf 2>/dev/null
   ```

⚠️ **IMPORTANTE:** Al corregir un parser, SIEMPRE verificar que no rompiste el procesamiento de facturas anteriores de ese proveedor. Si hay facturas de ejemplo en el proyecto, procesarlas todas.

### Categoría C — Parser funciona pero sinónimos faltan

**Síntoma:** El parser extrae los datos correctamente pero el matching contra artículos VeraBuy falla — aparecen como "sin match" o matchean al artículo equivocado.

**Qué hacer:**

1. Identificar qué líneas de la factura no matchearon:
   ```bash
   python procesar_pdf.py pendientes/NOMBRE_DEL_PDF.pdf 2>/dev/null | python -c "
   import sys, json
   data = json.load(sys.stdin)
   if data.get('ok'):
       for linea in data.get('lineas', data.get('lines', [])):
           # ⚠️ ADAPTAR: usar los nombres de campo reales
           match_type = linea.get('tipo_match', linea.get('match_type', 'unknown'))
           if match_type in ('none', 'no_match', '') or not linea.get('codigo_verabuy'):
               print(f'SIN MATCH: {linea.get(\"descripcion\", linea.get(\"description\", \"?\"))}')
   "
   ```

2. Para cada línea sin match, buscar manualmente el artículo VeraBuy correcto:
   ```bash
   # Buscar en los artículos VeraBuy
   python -c "
   # ⚠️ ADAPTAR: usar la función real de carga de artículos del proyecto
   # Buscar artículos que podrían corresponder
   import json
   # Intentar buscar por término
   termino = 'ROSA FREEDOM'  # ⚠️ ADAPTAR al producto real
   # ... búsqueda en el dump SQL o tabla de artículos ...
   "
   ```

3. Añadir los sinónimos faltantes:
   - Si es una tabla MySQL: INSERT directo
   - Si es sinonimos_universal.json: añadir la entrada
   ```bash
   python -c "
   import json
   with open('sinonimos_universal.json', 'r', encoding='utf-8') as f:
       sin = json.load(f)
   
   # ⚠️ ADAPTAR: usar la estructura real del JSON
   # Ejemplo: sin['CARN FANCY RED CERES'] = 12564
   sin['TÉRMINO_DEL_PROVEEDOR'] = CÓDIGO_VERABUY
   
   with open('sinonimos_universal.json', 'w', encoding='utf-8') as f:
       json.dump(sin, f, ensure_ascii=False, indent=2)
   
   print('Sinónimo añadido')
   "
   ```

4. Verificar:
   ```bash
   python procesar_pdf.py pendientes/NOMBRE_DEL_PDF.pdf
   ```
   Las líneas que antes no matcheaban ahora deben tener match.

### Categoría D — Múltiples problemas combinados

A veces una factura tiene varios problemas a la vez (parser parcialmente malo + sinónimos faltantes). En ese caso:

1. Corregir el parser PRIMERO (Categoría B)
2. Re-ejecutar para ver qué líneas siguen sin match
3. Añadir sinónimos para las que falten (Categoría C)
4. Verificar el resultado final completo

---

## Paso 4 — Verificación cruzada

Después de hacer TODOS los cambios, ejecutar una verificación global:

```bash
# 1. Todos los parsers compilan
python -c "from parsers import FORMAT_PARSERS; print(f'Parsers cargados: {len(FORMAT_PARSERS)}')"

# 2. Todos los PDFs pendientes ahora funcionan
for pdf in pendientes/*.pdf; do
    echo "=== Procesando: $pdf ==="
    python procesar_pdf.py "$pdf" 2>/dev/null | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('ok'):
        lineas = data.get('lineas', data.get('lines', []))
        matches = sum(1 for l in lineas if l.get('codigo_verabuy') or l.get('tipo_match','') not in ('none','no_match',''))
        print(f'  OK: {len(lineas)} líneas, {matches} matches')
    else:
        print(f'  ERROR: {data.get(\"error\", \"unknown\")}')
except:
    print('  ERROR: respuesta no es JSON válido')
"
done

# 3. Sinónimos JSON es válido (si aplica)
python -c "import json; json.load(open('sinonimos_universal.json', encoding='utf-8')); print('Sinónimos JSON OK')" 2>/dev/null

# 4. Config es válido
python -c "import config; print(f'Proveedores: {len(config.PROVIDERS)}')"

# 5. No hay errores de sintaxis en ningún parser
find parsers/ -name "*.py" -exec python -m py_compile {} \; && echo "Todos los parsers compilan OK"
```

---

## Paso 5 — Informe de cambios

Al terminar, generar un informe resumido:

```
═══════════════════════════════════════════════
INFORME DE MEJORAS — [FECHA]
═══════════════════════════════════════════════

FACTURAS PROCESADAS: X de Y

PARSERS NUEVOS CREADOS:
  - FloralCo (parsers/floralco.py) — tablas con 8 columnas, farm codes
  - TropicalExport (parsers/tropical.py) — texto plano con regex

PARSERS CORREGIDOS:
  - Golden (parsers/golden.py) — FIX: nueva columna "grade" añadida en 2025
  - Cantiza (parsers/cantiza.py) — FIX: regex no capturaba cajas mixtas con 3+ colores

SINÓNIMOS AÑADIDOS: N nuevos
  - "CARN FANCY RED CERES" → 12564 (CLAVEL COL FANCY ROJO 70CM 20U)
  - "HYD JUMBO BLUE ELITE" → 8891 (HORTENSIA ELITE AZUL)
  - ...

RESULTADOS:
  - XX/YY facturas ahora procesan correctamente
  - ZZ líneas con match exitoso
  - WW líneas aún sin match (listadas abajo para revisión manual)

PENDIENTE DE REVISIÓN MANUAL:
  - factura_X.pdf línea 4: "EXOTIC LILY SUNSET 90CM" — no se encontró artículo VeraBuy equivalente
```

---

## Paso 6 — Commit

```bash
git add -A
git commit -m "fix: mejorar parsers y sinónimos para N facturas nuevas

Parsers nuevos: [listar]
Parsers corregidos: [listar]
Sinónimos añadidos: N
Facturas resueltas: X de Y"
```

---

## Reglas importantes

1. **NUNCA modificar un parser sin antes leer los existentes.** Tu código DEBE seguir exactamente los mismos patrones, imports, y convenciones que los 27 parsers actuales.

2. **NUNCA asumir la estructura del PDF.** Siempre extraer el texto con pdfplumber PRIMERO y analizarlo antes de escribir regex.

3. **Cada parser nuevo debe funcionar con AL MENOS las facturas que tienes disponibles.** Si solo tienes 1 PDF de un proveedor nuevo, el parser debe funcionar con ese PDF. Si tienes 5, debe funcionar con los 5.

4. **Al corregir un parser existente, NO romper facturas anteriores.** Si hay PDFs de prueba del mismo proveedor, verificar que siguen funcionando.

5. **Los sinónimos deben ser lo más específicos posible.** No crear sinónimos genéricos ambiguos. Incluir la marca/farm cuando esté disponible en el nombre (ej: "ROSA FREEDOM CERES", no solo "ROSA FREEDOM").

6. **Documentar cada cambio.** Comentarios en el código explicando POR QUÉ se hizo el cambio, no solo QUÉ se cambió.

7. **No inventar artículos VeraBuy.** Si no puedes encontrar el artículo correspondiente en el inventario, NO crear un sinónimo con un código inventado. Dejarlo en el informe como "pendiente de revisión manual".

8. **Ser conservador con las regex.** Es mejor una regex que capture menos pero bien, que una que capture mucho pero mal. Si una regex falla en un caso edge, corregirla para ese caso sin hacerla tan amplia que genere falsos positivos.
