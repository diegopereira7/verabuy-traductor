# PROCESAMIENTO MASIVO - VUELOS 2026
# Uso: .\procesar_2026_v3.ps1

# --- CONFIGURACION ---
$RUTA_FACTURAS = "C:\Users\diego.pereira\Desktop\DOC VERA\FACTURAS IMPORTACION\VUELOS 2026"
$RUTA_PROYECTO = "C:\verabuy-traductor"
$TAMANO_LOTE = 150

# --- RUTAS ---
$DIR_INPUT   = Join-Path $RUTA_PROYECTO "batch_2026_input"
$DIR_LOTES   = Join-Path $RUTA_PROYECTO "batch_2026_lotes"
$DIR_RESULTS = Join-Path $RUTA_PROYECTO "batch_2026_resultados"
$DIR_FALLOS  = Join-Path $RUTA_PROYECTO "batch_2026_fallos"
$LOG_FILE    = Join-Path $RUTA_PROYECTO "batch_2026_log.txt"

function Log {
    param([string]$msg)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $msg"
    Write-Host $line
    $line | Out-File -FilePath $LOG_FILE -Append -Encoding UTF8
}

# ----------------------------------------------------------
# FASE 1: APLANAR CARPETAS
# ----------------------------------------------------------

Log "FASE 1: Aplanando estructura de carpetas"

foreach ($dir in @($DIR_INPUT, $DIR_LOTES, $DIR_RESULTS, $DIR_FALLOS)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

Log "Buscando PDFs en: $RUTA_FACTURAS"

$pdfs = Get-ChildItem -Path $RUTA_FACTURAS -Recurse -Filter "*.pdf"
$total = $pdfs.Count
Log "PDFs encontrados: $total"

if ($total -eq 0) {
    Log "ERROR: No se encontraron PDFs. Verifica la ruta."
    exit 1
}

$duplicados = 0
$copiados = 0
$nombres_usados = @{}

foreach ($pdf in $pdfs) {
    $nombre = $pdf.Name

    if ($nombres_usados.ContainsKey($nombre.ToLower())) {
        $duplicados++
        $ruta_rel = $pdf.Directory.FullName.Replace($RUTA_FACTURAS, "").Trim("\")
        $prefijo = $ruta_rel -replace "\\", "_" -replace " ", "_"
        $nombre = $prefijo + "_" + $pdf.Name
    }

    $nombres_usados[$nombre.ToLower()] = $true
    $destino = Join-Path $DIR_INPUT $nombre
    Copy-Item -Path $pdf.FullName -Destination $destino -Force
    $copiados++

    if ($copiados % 500 -eq 0) {
        Log "  Copiados: $copiados / $total"
    }
}

Log "Copia completada: $copiados PDFs - $duplicados renombrados"

# ----------------------------------------------------------
# FASE 2: DIVIDIR EN LOTES
# ----------------------------------------------------------

Log "FASE 2: Dividiendo en lotes de $TAMANO_LOTE"

$pdfs_input = Get-ChildItem -Path $DIR_INPUT -Filter "*.pdf" | Sort-Object Name
$total_pdfs = $pdfs_input.Count
$num_lotes = [int][math]::Ceiling($total_pdfs / $TAMANO_LOTE)

Log "Total PDFs: $total_pdfs - $num_lotes lotes"

for ($i = 0; $i -lt $total_pdfs; $i += $TAMANO_LOTE) {
    $num_lote = [int]([math]::Floor($i / $TAMANO_LOTE)) + 1
    $nombre_lote = "lote_" + $num_lote
    $dir_lote = Join-Path $DIR_LOTES $nombre_lote

    if (-not (Test-Path $dir_lote)) {
        New-Item -ItemType Directory -Path $dir_lote | Out-Null
    }

    $fin = [math]::Min($i + $TAMANO_LOTE - 1, $total_pdfs - 1)

    for ($j = $i; $j -le $fin; $j++) {
        Copy-Item -Path $pdfs_input[$j].FullName -Destination $dir_lote -Force
    }

    $count = (Get-ChildItem $dir_lote -Filter "*.pdf").Count
    Log "  Lote $num_lote : $count PDFs"
}

# ----------------------------------------------------------
# FASE 3: PROCESAR CADA LOTE
# ----------------------------------------------------------

Log "FASE 3: Procesando lotes"

$lotes = Get-ChildItem -Path $DIR_LOTES -Directory | Sort-Object Name
$lote_actual = 0
$total_ok = 0
$total_error = 0
$inicio_global = Get-Date

foreach ($lote in $lotes) {
    $lote_actual++
    $inicio_lote = Get-Date

    Log ""
    Log "--- Lote $lote_actual / $num_lotes : $($lote.Name) ---"

    $excel_output = Join-Path $DIR_RESULTS "$($lote.Name).xlsx"
    $log_output = Join-Path $DIR_RESULTS "$($lote.Name)_log.txt"

    # ADAPTAR: ajustar este comando a tu batch_process.py
    $script_path = Join-Path $RUTA_PROYECTO "batch_process.py"
    $carpeta_lote = $lote.FullName

    Log "  Ejecutando batch_process.py..."

    try {
        $proc = Start-Process -FilePath "python" `
            -ArgumentList "`"$script_path`" `"$carpeta_lote`" --output `"$excel_output`"" `
            -NoNewWindow -Wait -PassThru `
            -RedirectStandardOutput $log_output `
            -RedirectStandardError (Join-Path $DIR_RESULTS "$($lote.Name)_err.txt")

        if ($proc.ExitCode -eq 0) {
            Log "  Completado OK"
        } else {
            Log "  Completado con codigo de salida: $($proc.ExitCode)"
        }
    } catch {
        Log "  ERROR ejecutando: $_"
    }

    # Leer status JSON si existe
    $status_dir = Join-Path $RUTA_PROYECTO "batch_status"
    if (Test-Path $status_dir) {
        $status_file = Get-ChildItem $status_dir -Filter "*.json" -ErrorAction SilentlyContinue |
                       Sort-Object LastWriteTime -Descending | Select-Object -First 1

        if ($status_file) {
            try {
                $status = Get-Content $status_file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($status.resumen) {
                    $ok = [int]$status.resumen.procesadas_ok
                    $err = [int]$status.resumen.con_error
                    $total_ok += $ok
                    $total_error += $err
                    Log "  Resultado: $ok OK, $err errores"
                }
            } catch {
                Log "  No se pudo leer status JSON"
            }
        }
    }

    $duracion = (Get-Date) - $inicio_lote
    $mins = [math]::Round($duracion.TotalMinutes, 1)
    Log "  Duracion: $mins minutos"

    $lotes_restantes = $num_lotes - $lote_actual
    if ($mins -gt 0) {
        $tiempo_estimado = [math]::Round($mins * $lotes_restantes, 0)
        Log "  Estimado restante: ~$tiempo_estimado minutos ($lotes_restantes lotes)"
    }
}

$duracion_total = (Get-Date) - $inicio_global

# ----------------------------------------------------------
# FASE 4: SEPARAR FACTURAS QUE FALLARON
# ----------------------------------------------------------

Log ""
Log "FASE 4: Separando facturas con errores"

$archivos_error = @()
$status_dir = Join-Path $RUTA_PROYECTO "batch_status"

if (Test-Path $status_dir) {
    $status_files = Get-ChildItem $status_dir -Filter "*.json" -ErrorAction SilentlyContinue

    foreach ($sf in $status_files) {
        try {
            $status = Get-Content $sf.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($status.errores -and $status.errores.Count -gt 0) {
                foreach ($e in $status.errores) {
                    if ($e.archivo) {
                        $archivos_error += $e.archivo
                    }
                }
            }
        } catch {}
    }
}

if ($archivos_error.Count -gt 0) {
    Log "Facturas con error: $($archivos_error.Count)"

    foreach ($nombre in $archivos_error) {
        $origen = Get-ChildItem -Path $DIR_INPUT -Filter $nombre -ErrorAction SilentlyContinue
        if ($origen) {
            Copy-Item -Path $origen.FullName -Destination $DIR_FALLOS -Force
        }
    }

    Log "Copiadas a: $DIR_FALLOS"
} else {
    Log "No se encontraron errores en los status JSON"
    Log "Revisar manualmente los Excel en: $DIR_RESULTS"
}

# ----------------------------------------------------------
# FASE 5: INFORME RESUMEN
# ----------------------------------------------------------

Log ""
Log "======================================================"
Log "              INFORME FINAL"
Log "======================================================"
Log ""
Log "  PDFs totales:        $total"
Log "  Lotes procesados:    $num_lotes"
Log "  Procesadas OK:       $total_ok"
Log "  Con errores:         $total_error"

$denominador = $total_ok + $total_error
if ($denominador -gt 0) {
    $tasa = [math]::Round(($total_ok / $denominador) * 100, 1)
} else {
    $tasa = 0
}

Log "  Tasa de exito:       $tasa%"

$mins_total = [math]::Round($duracion_total.TotalMinutes, 1)
Log "  Duracion total:      $mins_total minutos"
Log ""
Log "  Resultados Excel:    $DIR_RESULTS"
Log "  Facturas fallidas:   $DIR_FALLOS"
Log "  Log completo:        $LOG_FILE"
Log ""

if ($total_error -gt 0) {
    Log "  SIGUIENTE PASO:"
    Log "  Copia las facturas de $DIR_FALLOS a pendientes/"
    Log "  en Claude Code y usa el prompt de analisis."
}

Log "======================================================"
