<?php
/**
 * VeraBuy Traductor Web - API endpoint
 * Recibe un PDF vía POST y devuelve el resultado del procesamiento en JSON.
 */
require_once __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Método no permitido']);
    exit;
}

$action = $_GET['action'] ?? 'process';

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
