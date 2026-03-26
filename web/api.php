<?php
/**
 * VeraBuy Traductor Web - API endpoint
 * Recibe un PDF vía POST y devuelve el resultado del procesamiento en JSON.
 */
require_once __DIR__ . '/config.php';

// Constantes de importación masiva
define('BATCH_STATUS_DIR',  PROJECT_ROOT . '/batch_status');
define('BATCH_RESULTS_DIR', PROJECT_ROOT . '/batch_results');
define('BATCH_UPLOADS_DIR', PROJECT_ROOT . '/batch_uploads');
define('BATCH_SCRIPT',      PROJECT_ROOT . '/batch_process.py');
define('MAX_ZIP_SIZE',      100 * 1024 * 1024); // 100 MB

header('Content-Type: application/json; charset=utf-8');

// Batch status y download son GET; el resto POST
$action = $_GET['action'] ?? 'process';

if (in_array($action, ['batch_status', 'batch_download'])) {
    if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
        http_response_code(405);
        echo json_encode(['ok' => false, 'error' => 'Método no permitido']);
        exit;
    }
} else {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        http_response_code(405);
        echo json_encode(['ok' => false, 'error' => 'Método no permitido']);
        exit;
    }
}

switch ($action) {
    case 'process':
        handleProcess();
        break;
    case 'synonyms':
        handleSynonyms();
        break;
    case 'history':
        handleHistory();
        break;
    case 'save_synonym':
        handleSaveSynonym();
        break;
    case 'batch_upload':
        handleBatchUpload();
        break;
    case 'batch_status':
        handleBatchStatus();
        break;
    case 'batch_download':
        handleBatchDownload();
        break;
    default:
        http_response_code(400);
        echo json_encode(['ok' => false, 'error' => 'Acción no válida']);
}

/**
 * Procesar un PDF subido
 */
function handleProcess(): void
{
    if (!isset($_FILES['pdf']) || $_FILES['pdf']['error'] !== UPLOAD_ERR_OK) {
        $code = $_FILES['pdf']['error'] ?? -1;
        echo json_encode(['ok' => false, 'error' => "Error al subir archivo (código $code)"]);
        return;
    }

    $file = $_FILES['pdf'];

    // Validar tipo
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime = finfo_file($finfo, $file['tmp_name']);
    finfo_close($finfo);

    if ($mime !== 'application/pdf') {
        echo json_encode(['ok' => false, 'error' => 'El archivo debe ser un PDF']);
        return;
    }

    // Validar tamaño
    if ($file['size'] > MAX_PDF_SIZE) {
        echo json_encode(['ok' => false, 'error' => 'El archivo excede el tamaño máximo (10 MB)']);
        return;
    }

    // Guardar con nombre seguro
    $safeName = preg_replace('/[^a-zA-Z0-9._-]/', '_', basename($file['name']));
    $dest = UPLOAD_DIR . '/' . time() . '_' . $safeName;

    if (!move_uploaded_file($file['tmp_name'], $dest)) {
        echo json_encode(['ok' => false, 'error' => 'Error al guardar el archivo']);
        return;
    }

    // Llamar al procesador Python
    // En Windows, escapeshellarg usa comillas dobles; construimos el comando
    // con la ruta absoluta al intérprete para evitar problemas de PATH en WAMP.
    $cmd = '"' . PYTHON_BIN . '" '
         . '"' . PROCESSOR_SCRIPT . '" '
         . '"' . $dest . '"'
         . ' 2>&1';

    $output = shell_exec($cmd);

    // Limpiar archivo subido
    @unlink($dest);

    if ($output === null) {
        echo json_encode(['ok' => false, 'error' => 'Error al ejecutar el procesador Python']);
        return;
    }

    // El procesador devuelve JSON directamente
    echo $output;
}

/**
 * Devolver sinónimos actuales
 */
function handleSynonyms(): void
{
    if (!file_exists(SYNONYMS_FILE)) {
        echo json_encode(['ok' => true, 'synonyms' => []]);
        return;
    }

    $data = json_decode(file_get_contents(SYNONYMS_FILE), true);
    if ($data === null) {
        echo json_encode(['ok' => false, 'error' => 'Error al leer sinónimos']);
        return;
    }

    // Convertir a array indexado para la tabla
    $list = [];
    foreach ($data as $key => $entry) {
        $entry['key'] = $key;
        $list[] = $entry;
    }

    echo json_encode(['ok' => true, 'synonyms' => $list, 'total' => count($list)]);
}

/**
 * Devolver historial de procesamiento
 */
function handleHistory(): void
{
    if (!file_exists(HISTORY_FILE)) {
        echo json_encode(['ok' => true, 'history' => []]);
        return;
    }

    $data = json_decode(file_get_contents(HISTORY_FILE), true);
    if ($data === null) {
        echo json_encode(['ok' => false, 'error' => 'Error al leer historial']);
        return;
    }

    $list = [];
    foreach ($data as $key => $entry) {
        $entry['invoice_key'] = $key;
        $list[] = $entry;
    }

    // Ordenar por fecha descendente
    usort($list, fn($a, $b) => strcmp($b['fecha'] ?? '', $a['fecha'] ?? ''));

    echo json_encode(['ok' => true, 'history' => $list, 'total' => count($list)]);
}

/**
 * Guardar un sinónimo manual (resolver sin_match)
 */
function handleSaveSynonym(): void
{
    $input = json_decode(file_get_contents('php://input'), true);

    if (!$input || empty($input['key']) || empty($input['articulo_id'])) {
        echo json_encode(['ok' => false, 'error' => 'Datos incompletos']);
        return;
    }

    if (!file_exists(SYNONYMS_FILE)) {
        echo json_encode(['ok' => false, 'error' => 'Archivo de sinónimos no encontrado']);
        return;
    }

    $data = json_decode(file_get_contents(SYNONYMS_FILE), true);
    if ($data === null) {
        echo json_encode(['ok' => false, 'error' => 'Error al leer sinónimos']);
        return;
    }

    $key = $input['key'];
    $data[$key] = [
        'articulo_id'    => (int)$input['articulo_id'],
        'articulo_name'  => $input['articulo_name'] ?? '',
        'origen'         => 'manual-web',
        'provider_id'    => (int)($input['provider_id'] ?? 0),
        'species'        => $input['species'] ?? '',
        'variety'        => $input['variety'] ?? '',
        'size'           => (int)($input['size'] ?? 0),
        'stems_per_bunch' => (int)($input['stems_per_bunch'] ?? 0),
        'grade'          => $input['grade'] ?? '',
    ];

    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    if (file_put_contents(SYNONYMS_FILE, $json) === false) {
        echo json_encode(['ok' => false, 'error' => 'Error al guardar sinónimos']);
        return;
    }

    echo json_encode(['ok' => true, 'message' => 'Sinónimo guardado']);
}

// ── Importación Masiva ──────────────────────────────────────────────────────

/**
 * Subir ZIP con PDFs y lanzar procesamiento en background
 */
function handleBatchUpload(): void
{
    // Verificar que no hay batch en curso
    $running = _findRunningBatch();
    if ($running) {
        echo json_encode([
            'ok' => false,
            'error' => 'Ya hay un lote en proceso. Espera a que termine.',
            'batch_id' => $running,
        ]);
        return;
    }

    if (!isset($_FILES['zip']) || $_FILES['zip']['error'] !== UPLOAD_ERR_OK) {
        $code = $_FILES['zip']['error'] ?? -1;
        echo json_encode(['ok' => false, 'error' => "Error al subir archivo (código $code)"]);
        return;
    }

    $file = $_FILES['zip'];

    // Validar tipo
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime = finfo_file($finfo, $file['tmp_name']);
    finfo_close($finfo);

    if (!in_array($mime, ['application/zip', 'application/x-zip-compressed', 'application/octet-stream'])) {
        echo json_encode(['ok' => false, 'error' => "El archivo debe ser un ZIP (recibido: $mime)"]);
        return;
    }

    if ($file['size'] > MAX_ZIP_SIZE) {
        echo json_encode(['ok' => false, 'error' => 'El ZIP excede el tamaño máximo (100 MB)']);
        return;
    }

    // Generar batch ID
    $batchId = date('YmdHis') . '_' . bin2hex(random_bytes(4));

    // Descomprimir ZIP
    $extractDir = BATCH_UPLOADS_DIR . '/' . $batchId;
    @mkdir($extractDir, 0777, true);

    $zip = new ZipArchive();
    if ($zip->open($file['tmp_name']) !== true) {
        echo json_encode(['ok' => false, 'error' => 'No se pudo abrir el archivo ZIP']);
        @rmdir($extractDir);
        return;
    }

    // Extraer solo PDFs (evitar archivos peligrosos)
    $pdfCount = 0;
    for ($i = 0; $i < $zip->numFiles; $i++) {
        $name = $zip->getNameIndex($i);
        // Ignorar directorios y archivos no-PDF
        if (substr($name, -1) === '/' || strtolower(pathinfo($name, PATHINFO_EXTENSION)) !== 'pdf') {
            continue;
        }
        // Usar solo el basename (evitar path traversal)
        $safeName = preg_replace('/[^a-zA-Z0-9._-]/', '_', basename($name));
        // Evitar colisiones
        $dest = $extractDir . '/' . $safeName;
        if (file_exists($dest)) {
            $safeName = pathinfo($safeName, PATHINFO_FILENAME) . '_' . $i . '.pdf';
            $dest = $extractDir . '/' . $safeName;
        }
        // Extraer a memoria y guardar
        $content = $zip->getFromIndex($i);
        if ($content !== false) {
            file_put_contents($dest, $content);
            $pdfCount++;
        }
    }
    $zip->close();

    if ($pdfCount === 0) {
        // Limpiar
        array_map('unlink', glob($extractDir . '/*'));
        @rmdir($extractDir);
        echo json_encode(['ok' => false, 'error' => 'El ZIP no contiene archivos PDF']);
        return;
    }

    // Lanzar Python en background
    $cmd = '"' . PYTHON_BIN . '" '
         . '"' . BATCH_SCRIPT . '" '
         . '"' . $extractDir . '" '
         . '--batch-id ' . $batchId;

    // Windows: start /B para background
    $bgCmd = 'start /B cmd /C "' . $cmd . ' > nul 2>&1"';
    pclose(popen($bgCmd, 'r'));

    echo json_encode([
        'ok'        => true,
        'batch_id'  => $batchId,
        'total_pdfs' => $pdfCount,
    ]);
}

/**
 * Consultar estado de un batch
 */
function handleBatchStatus(): void
{
    $batchId = $_GET['batch_id'] ?? '';
    if (!preg_match('/^[a-zA-Z0-9_]+$/', $batchId)) {
        echo json_encode(['ok' => false, 'error' => 'batch_id inválido']);
        return;
    }

    $statusFile = BATCH_STATUS_DIR . '/' . $batchId . '.json';

    if (!file_exists($statusFile)) {
        // Puede que Python aún no haya escrito el primer status
        echo json_encode([
            'ok' => true,
            'estado' => 'iniciando',
            'progreso' => 0, 'total' => 0, 'porcentaje' => 0,
            'actual' => 'Iniciando procesamiento...',
            'procesados_ok' => 0, 'con_error' => 0,
        ]);
        return;
    }

    $content = @file_get_contents($statusFile);
    if ($content === false) {
        echo json_encode(['ok' => false, 'error' => 'Error al leer estado']);
        return;
    }

    $data = json_decode($content, true);
    if ($data === null) {
        echo json_encode(['ok' => true, 'estado' => 'iniciando', 'progreso' => 0, 'total' => 0, 'porcentaje' => 0]);
        return;
    }

    $data['ok'] = true;
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
}

/**
 * Descargar Excel de resultados de un batch
 */
function handleBatchDownload(): void
{
    $batchId = $_GET['batch_id'] ?? '';
    if (!preg_match('/^[a-zA-Z0-9_]+$/', $batchId)) {
        http_response_code(400);
        echo json_encode(['ok' => false, 'error' => 'batch_id inválido']);
        return;
    }

    $excelFile = BATCH_RESULTS_DIR . '/' . $batchId . '.xlsx';

    if (!file_exists($excelFile)) {
        http_response_code(404);
        echo json_encode(['ok' => false, 'error' => 'Excel no encontrado']);
        return;
    }

    header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    header('Content-Disposition: attachment; filename="verabuy_batch_' . $batchId . '.xlsx"');
    header('Content-Length: ' . filesize($excelFile));
    readfile($excelFile);
    exit;
}

/**
 * Buscar si hay algún batch en curso (no completado ni error)
 */
function _findRunningBatch(): ?string
{
    $files = glob(BATCH_STATUS_DIR . '/*.json');
    foreach ($files as $f) {
        $content = @file_get_contents($f);
        if ($content === false) continue;
        $data = json_decode($content, true);
        if ($data && isset($data['estado']) && !in_array($data['estado'], ['completado', 'error'])) {
            // Verificar que no sea un zombie (>30 min sin actualizar)
            if (isset($data['timestamp'])) {
                $ts = strtotime($data['timestamp']);
                if ($ts && (time() - $ts) > 1800) {
                    continue; // Zombie, ignorar
                }
            }
            return pathinfo($f, PATHINFO_FILENAME);
        }
    }
    return null;
}
