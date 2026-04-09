<?php
/**
 * VeraBuy Traductor Web - API endpoint
 * Recibe un PDF vía POST y devuelve el resultado del procesamiento en JSON.
 */
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/db_config.php';

// Constantes de importación masiva
define('BATCH_STATUS_DIR',  PROJECT_ROOT . '/batch_status');
define('BATCH_RESULTS_DIR', PROJECT_ROOT . '/batch_results');
define('BATCH_UPLOADS_DIR', PROJECT_ROOT . '/batch_uploads');
define('BATCH_SCRIPT',      PROJECT_ROOT . '/batch_process.py');
define('MAX_ZIP_SIZE',      100 * 1024 * 1024); // 100 MB
define('LEARNED_RULES_FILE', PROJECT_ROOT . '/learned_rules.json');
define('PENDING_REVIEW_FILE', PROJECT_ROOT . '/pending_review.json');
define('AUDIT_LOG_FILE', PROJECT_ROOT . '/audit_log.jsonl');

header('Content-Type: application/json; charset=utf-8');

// Batch status y download son GET; el resto POST
$action = $_GET['action'] ?? 'process';

if (in_array($action, ['batch_status', 'batch_download', 'learned_parsers', 'pending_review', 'lookup_article'])) {
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
    case 'update_synonym':
        handleUpdateSynonym();
        break;
    case 'lookup_article':
        handleLookupArticle();
        break;
    case 'delete_synonym':
        handleDeleteSynonym();
        break;
    case 'reprocess':
        handleReprocess();
        break;
    case 'batch_upload':
        handleBatchUpload();
        break;
    case 'batch_upload_pdfs':
        handleBatchUploadPdfs();
        break;
    case 'batch_status':
        handleBatchStatus();
        break;
    case 'batch_download':
        handleBatchDownload();
        break;
    case 'learned_parsers':
        handleLearnedParsers();
        break;
    case 'pending_review':
        handlePendingReview();
        break;
    case 'toggle_parser':
        handleToggleParser();
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
 * Devolver sinónimos actuales (MySQL con fallback JSON)
 */
function handleSynonyms(): void
{
    $db = get_db();
    if ($db) {
        $result = $db->query("SELECT clave AS `key`, articulo_id, articulo_name,
            origen, provider_id, species, variety, size, stems_per_bunch, grade,
            raw, invoice FROM sinonimos WHERE activo = 1 ORDER BY clave");
        if ($result) {
            $list = $result->fetch_all(MYSQLI_ASSOC);
            // Convertir tipos numéricos
            foreach ($list as &$row) {
                $row['articulo_id'] = (int)$row['articulo_id'];
                $row['provider_id'] = (int)$row['provider_id'];
                $row['size'] = (int)$row['size'];
                $row['stems_per_bunch'] = (int)$row['stems_per_bunch'];
            }
            echo json_encode(['ok' => true, 'synonyms' => $list, 'total' => count($list)]);
            return;
        }
    }

    // Fallback a JSON
    if (!file_exists(SYNONYMS_FILE)) {
        echo json_encode(['ok' => true, 'synonyms' => []]);
        return;
    }
    $data = json_decode(file_get_contents(SYNONYMS_FILE), true);
    if ($data === null) {
        echo json_encode(['ok' => false, 'error' => 'Error al leer sinónimos']);
        return;
    }
    $list = [];
    foreach ($data as $key => $entry) {
        $entry['key'] = $key;
        $list[] = $entry;
    }
    echo json_encode(['ok' => true, 'synonyms' => $list, 'total' => count($list)]);
}

/**
 * Devolver historial de procesamiento (MySQL con fallback JSON)
 */
function handleHistory(): void
{
    $db = get_db();
    if ($db) {
        $result = $db->query("SELECT invoice_key, pdf, provider, total_usd,
            lineas, ok, sin_match, fecha FROM historial ORDER BY fecha DESC");
        if ($result) {
            $list = $result->fetch_all(MYSQLI_ASSOC);
            foreach ($list as &$row) {
                $row['total_usd'] = (float)$row['total_usd'];
                $row['lineas'] = (int)$row['lineas'];
                $row['ok'] = (int)$row['ok'];
                $row['sin_match'] = (int)$row['sin_match'];
            }
            echo json_encode(['ok' => true, 'history' => $list, 'total' => count($list)]);
            return;
        }
    }

    // Fallback JSON
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
    usort($list, fn($a, $b) => strcmp($b['fecha'] ?? '', $a['fecha'] ?? ''));
    echo json_encode(['ok' => true, 'history' => $list, 'total' => count($list)]);
}

/**
 * Guardar un sinónimo manual — MySQL + JSON dual-write
 */
function handleSaveSynonym(): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input || empty($input['key']) || empty($input['articulo_id'])) {
        echo json_encode(['ok' => false, 'error' => 'Datos incompletos']);
        return;
    }

    $key = $input['key'];
    $artId = (int)$input['articulo_id'];
    $artName = $input['articulo_name'] ?? '';

    // MySQL
    $db = get_db();
    if ($db) {
        $stmt = $db->prepare("INSERT INTO sinonimos (clave, articulo_id, articulo_name, origen)
            VALUES (?, ?, ?, 'manual-web')
            ON DUPLICATE KEY UPDATE articulo_id=VALUES(articulo_id),
            articulo_name=VALUES(articulo_name), origen='manual-web'");
        $stmt->bind_param('sis', $key, $artId, $artName);
        $stmt->execute();
    }

    // JSON sync
    _syncSynonymToJson($key, [
        'articulo_id' => $artId, 'articulo_name' => $artName, 'origen' => 'manual-web',
        'provider_id' => (int)($input['provider_id'] ?? 0),
        'species' => $input['species'] ?? '', 'variety' => $input['variety'] ?? '',
        'size' => (int)($input['size'] ?? 0), 'stems_per_bunch' => (int)($input['stems_per_bunch'] ?? 0),
        'grade' => $input['grade'] ?? '',
    ]);

    echo json_encode(['ok' => true, 'message' => 'Sinónimo guardado']);
}

/**
 * Buscar nombre de artículo por ID — MySQL con fallback SQL dump
 */
function handleLookupArticle(): void
{
    $id = (int)($_GET['id'] ?? 0);
    if (!$id) {
        echo json_encode(['ok' => false, 'error' => 'ID no proporcionado']);
        return;
    }

    // MySQL primero
    $db = get_db();
    if ($db) {
        $stmt = $db->prepare("SELECT nombre FROM articulos WHERE id = ? LIMIT 1");
        $stmt->bind_param('i', $id);
        $stmt->execute();
        $result = $stmt->get_result();
        if ($row = $result->fetch_assoc()) {
            echo json_encode(['ok' => true, 'id' => $id, 'nombre' => $row['nombre']]);
            return;
        }
    }

    // Fallback: regex en dump SQL
    $sqlFile = PROJECT_ROOT . '/articulos (3).sql';
    if (!file_exists($sqlFile)) {
        echo json_encode(['ok' => false, 'error' => "Artículo $id no encontrado"]);
        return;
    }
    $content = file_get_contents($sqlFile);
    $pattern = "/\($id,\s*'[^']*',\s*\d+,\s*\d+,\s*(?:'[^']*'|NULL),\s*(?:'[^']*'|NULL),\s*(?:'[^']*'|NULL),\s*\d+,\s*'([^']+)'/";
    if (preg_match($pattern, $content, $m)) {
        echo json_encode(['ok' => true, 'id' => $id, 'nombre' => $m[1]]);
    } else {
        echo json_encode(['ok' => false, 'error' => "Artículo $id no encontrado"]);
    }
}

/**
 * Actualizar sinónimo — MySQL + JSON dual-write
 */
function handleUpdateSynonym(): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    $origKey = $input['original_key'] ?? '';
    $newKey  = $input['new_key'] ?? '';
    $artId   = (int)($input['articulo_id'] ?? 0);
    $artName = $input['articulo_name'] ?? '';

    if (!$origKey || !$newKey || !$artId) {
        echo json_encode(['ok' => false, 'error' => 'Datos incompletos']);
        return;
    }

    // MySQL
    $db = get_db();
    if ($db) {
        if ($origKey !== $newKey) {
            // Cambiar clave: borrar vieja, insertar nueva
            $stmt = $db->prepare("DELETE FROM sinonimos WHERE clave = ?");
            $stmt->bind_param('s', $origKey);
            $stmt->execute();
        }
        $stmt = $db->prepare("INSERT INTO sinonimos (clave, articulo_id, articulo_name, origen)
            VALUES (?, ?, ?, 'manual-web')
            ON DUPLICATE KEY UPDATE articulo_id=VALUES(articulo_id),
            articulo_name=VALUES(articulo_name), origen='manual-web'");
        $stmt->bind_param('sis', $newKey, $artId, $artName);
        $stmt->execute();
    }

    // JSON sync
    $data = json_decode(file_get_contents(SYNONYMS_FILE), true) ?? [];
    if (isset($data[$origKey])) {
        $entry = $data[$origKey];
        $entry['articulo_id'] = $artId;
        $entry['articulo_name'] = $artName;
        $entry['origen'] = 'manual-web';
        if ($origKey !== $newKey) unset($data[$origKey]);
        $data[$newKey] = $entry;
        $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
        file_put_contents(SYNONYMS_FILE . '.tmp', $json);
        rename(SYNONYMS_FILE . '.tmp', SYNONYMS_FILE);
    }

    echo json_encode(['ok' => true, 'message' => 'Sinónimo actualizado']);
}

/**
 * Eliminar sinónimo — soft delete en MySQL + borrar de JSON
 */
function handleDeleteSynonym(): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    $key = $input['key'] ?? '';

    if (!$key) {
        echo json_encode(['ok' => false, 'error' => 'Clave no proporcionada']);
        return;
    }

    // MySQL: soft delete
    $db = get_db();
    if ($db) {
        $stmt = $db->prepare("UPDATE sinonimos SET activo = 0 WHERE clave = ?");
        $stmt->bind_param('s', $key);
        $stmt->execute();
    }

    // JSON: hard delete
    $data = json_decode(file_get_contents(SYNONYMS_FILE), true) ?? [];

    if (!isset($data[$key])) {
        echo json_encode(['ok' => false, 'error' => 'Sinónimo no encontrado']);
        return;
    }

    unset($data[$key]);

    $tmp = SYNONYMS_FILE . '.tmp';
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    file_put_contents($tmp, $json);
    rename($tmp, SYNONYMS_FILE);

    echo json_encode(['ok' => true, 'message' => 'Sinónimo eliminado']);
}

/**
 * Reprocesar un PDF del historial y devolver las líneas
 */
function handleReprocess(): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    $pdfName = $input['pdf'] ?? '';

    if (!$pdfName) {
        echo json_encode(['ok' => false, 'error' => 'Nombre de PDF no proporcionado']);
        return;
    }

    // Buscar el PDF en facturas/
    $pdfPath = PROJECT_ROOT . '/facturas/' . $pdfName;
    if (!file_exists($pdfPath)) {
        echo json_encode(['ok' => false, 'error' => "PDF no encontrado: $pdfName"]);
        return;
    }

    // Llamar a procesar_pdf.py
    $cmd = '"' . PYTHON_BIN . '" '
         . '"' . PROCESSOR_SCRIPT . '" '
         . '"' . $pdfPath . '"'
         . ' 2>&1';
    $output = shell_exec($cmd);

    if ($output === null) {
        echo json_encode(['ok' => false, 'error' => 'Error al ejecutar el procesador Python']);
        return;
    }

    echo $output;
}

/**
 * Sincroniza un sinónimo al fichero JSON (para compatibilidad con Python)
 */
function _syncSynonymToJson(string $key, array $entry): void
{
    $data = [];
    if (file_exists(SYNONYMS_FILE)) {
        $data = json_decode(file_get_contents(SYNONYMS_FILE), true) ?? [];
    }
    $data[$key] = $entry;
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    $tmp = SYNONYMS_FILE . '.tmp';
    file_put_contents($tmp, $json);
    rename($tmp, SYNONYMS_FILE);
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
 * Subir PDFs sueltos (desde carpeta o selección múltiple) y lanzar procesamiento
 */
function handleBatchUploadPdfs(): void
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

    if (!isset($_FILES['pdfs']) || !is_array($_FILES['pdfs']['name'])) {
        echo json_encode(['ok' => false, 'error' => 'No se recibieron archivos PDF']);
        return;
    }

    $batchId = date('YmdHis') . '_' . bin2hex(random_bytes(4));
    $extractDir = BATCH_UPLOADS_DIR . '/' . $batchId;
    @mkdir($extractDir, 0777, true);

    $pdfCount = 0;
    $fileCount = count($_FILES['pdfs']['name']);

    for ($i = 0; $i < $fileCount; $i++) {
        if ($_FILES['pdfs']['error'][$i] !== UPLOAD_ERR_OK) continue;

        $name = $_FILES['pdfs']['name'][$i];
        if (strtolower(pathinfo($name, PATHINFO_EXTENSION)) !== 'pdf') continue;

        $safeName = preg_replace('/[^a-zA-Z0-9._-]/', '_', basename($name));
        $dest = $extractDir . '/' . $safeName;

        // Evitar colisiones
        if (file_exists($dest)) {
            $safeName = pathinfo($safeName, PATHINFO_FILENAME) . '_' . $i . '.pdf';
            $dest = $extractDir . '/' . $safeName;
        }

        if (move_uploaded_file($_FILES['pdfs']['tmp_name'][$i], $dest)) {
            $pdfCount++;
        }
    }

    if ($pdfCount === 0) {
        array_map('unlink', glob($extractDir . '/*'));
        @rmdir($extractDir);
        echo json_encode(['ok' => false, 'error' => 'No se recibieron archivos PDF válidos']);
        return;
    }

    // Lanzar Python en background
    $cmd = '"' . PYTHON_BIN . '" '
         . '"' . BATCH_SCRIPT . '" '
         . '"' . $extractDir . '" '
         . '--batch-id ' . $batchId;

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

// ── Auto-Aprendizaje ────────────────────────────────────────────────────────

/**
 * Lista de parsers aprendidos
 */
function handleLearnedParsers(): void
{
    if (!file_exists(LEARNED_RULES_FILE)) {
        echo json_encode(['ok' => true, 'parsers' => [], 'total' => 0]);
        return;
    }

    $data = json_decode(file_get_contents(LEARNED_RULES_FILE), true);
    if ($data === null) {
        echo json_encode(['ok' => true, 'parsers' => [], 'total' => 0]);
        return;
    }

    $list = [];
    foreach ($data as $name => $config) {
        $list[] = [
            'nombre'       => $name,
            'species'      => $config['species'] ?? '',
            'score'        => $config['score'] ?? 0,
            'decision'     => $config['decision'] ?? '',
            'fecha'        => $config['fecha_generacion'] ?? '',
            'num_pdfs'     => $config['num_pdfs_analizados'] ?? 0,
            'activo'       => $config['activo'] ?? true,
            'keywords'     => $config['keywords'] ?? [],
        ];
    }

    echo json_encode(['ok' => true, 'parsers' => $list, 'total' => count($list)]);
}

/**
 * Pendientes de revisión
 */
function handlePendingReview(): void
{
    if (!file_exists(PENDING_REVIEW_FILE)) {
        echo json_encode(['ok' => true, 'pendientes' => []]);
        return;
    }

    $data = json_decode(file_get_contents(PENDING_REVIEW_FILE), true);
    echo json_encode(['ok' => true, 'pendientes' => $data['pendientes'] ?? []]);
}

/**
 * Activar/desactivar un parser aprendido
 */
function handleToggleParser(): void
{
    $input = json_decode(file_get_contents('php://input'), true);
    $name = $input['nombre'] ?? '';

    if (!$name || !file_exists(LEARNED_RULES_FILE)) {
        echo json_encode(['ok' => false, 'error' => 'Parser no encontrado']);
        return;
    }

    $data = json_decode(file_get_contents(LEARNED_RULES_FILE), true);
    if (!isset($data[$name])) {
        echo json_encode(['ok' => false, 'error' => 'Parser no encontrado']);
        return;
    }

    $data[$name]['activo'] = !($data[$name]['activo'] ?? true);
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    file_put_contents(LEARNED_RULES_FILE, $json);

    $state = $data[$name]['activo'] ? 'activado' : 'desactivado';
    echo json_encode(['ok' => true, 'message' => "Parser $name $state", 'activo' => $data[$name]['activo']]);
}
