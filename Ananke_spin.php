<?php
declare(strict_types=1);

ini_set('display_errors', '0');
ini_set('display_startup_errors', '0');
error_reporting(E_ALL);

if (!headers_sent()) {
    header('Content-Type: application/json; charset=UTF-8');
    header('Cache-Control: no-store, private');
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('Strict-Transport-Security: max-age=31536000; includeSubDomains');
}

require_once __DIR__ . '/private/Ananke_access.php';

const ANANKE_MAX_UPLOAD = 52428800;
const ANANKE_ALLOWED_EXTENSIONS = [
    'txt','md','markdown','csv','tsv','json','jsonl','html','htm','xml','log','sql','php','js','ts','py','css','yaml','yml','pdf'
];

try {
    $method = (string)($_SERVER['REQUEST_METHOD'] ?? '');
    if (!in_array($method, ['GET', 'POST'], true)) {
        ananke_respond(405, ['error' => 'method_not_allowed']);
    }

    $access = ananke_access_context();
    $action = (string)($_GET['action'] ?? $_POST['action'] ?? '');

    if ($action === 'access_status' || ($method === 'GET' && $action === '')) {
        ananke_respond(200, [
            ...$access,
            'csrf_token' => $access['authenticated'] ? ananke_csrf_token() : null,
            'max_upload_bytes' => ANANKE_MAX_UPLOAD,
            'runtime' => 'php-direct-python',
        ]);
    }

    if (!$access['authenticated']) {
        ananke_respond(401, ['error' => 'authentication_required']);
    }
    if (!$access['granted']) {
        ananke_respond(403, ['error' => 'ananke_access_denied']);
    }

    if ($method === 'GET') {
        if ($action === 'stats') {
            ananke_run_python(['action' => 'stats'], 30);
        }
        ananke_respond(400, ['error' => 'unknown_action']);
    }

    ananke_require_csrf();

    if (str_starts_with(strtolower((string)($_SERVER['CONTENT_TYPE'] ?? '')), 'multipart/form-data')) {
        ananke_handle_upload($access);
    }

    $raw = file_get_contents('php://input');
    if ($raw === false || trim($raw) === '') {
        ananke_respond(400, ['error' => 'empty_body']);
    }
    $payload = json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
    if (!is_array($payload)) {
        ananke_respond(400, ['error' => 'invalid_payload']);
    }
    $payload['action'] = (string)($payload['action'] ?? 'infer');
    $payload['user_id'] = (int)$access['user_id'];
    $allowed = ['infer','chat','learning_commit','learning_discard','referential_view'];
    if (!in_array($payload['action'], $allowed, true)) {
        ananke_respond(400, ['error' => 'unknown_action']);
    }
    $timeout = in_array($payload['action'], ['learning_commit'], true) ? 1200 : 180;
    ananke_run_python($payload, $timeout);
} catch (JsonException $exception) {
    ananke_respond(400, ['error' => 'invalid_json', 'detail' => $exception->getMessage()]);
} catch (Throwable $exception) {
    $status = str_contains($exception->getMessage(), 'CSRF') ? 403 : 500;
    ananke_respond($status, ['error' => 'ananke_spin_error', 'detail' => $exception->getMessage()]);
}

function ananke_handle_upload(array $access): never
{
    if ((string)($_POST['action'] ?? '') !== 'learning_analyze') {
        ananke_respond(400, ['error' => 'unknown_multipart_action']);
    }
    if (!isset($_FILES['learning_file']) || !is_array($_FILES['learning_file'])) {
        ananke_respond(400, ['error' => 'missing_learning_file']);
    }
    $file = $_FILES['learning_file'];
    $error = (int)($file['error'] ?? UPLOAD_ERR_NO_FILE);
    if ($error !== UPLOAD_ERR_OK) {
        ananke_respond(400, ['error' => 'upload_failed', 'upload_code' => $error]);
    }
    $size = (int)($file['size'] ?? 0);
    if ($size <= 0 || $size > ANANKE_MAX_UPLOAD) {
        ananke_respond(413, ['error' => 'file_too_large', 'max_bytes' => ANANKE_MAX_UPLOAD]);
    }
    $originalName = basename((string)($file['name'] ?? 'learning.txt'));
    $extension = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    if (!in_array($extension, ANANKE_ALLOWED_EXTENSIONS, true)) {
        ananke_respond(415, ['error' => 'unsupported_file_type', 'extension' => $extension]);
    }
    $temporary = (string)($file['tmp_name'] ?? '');
    if ($temporary === '' || !is_uploaded_file($temporary)) {
        ananke_respond(400, ['error' => 'invalid_upload']);
    }
    $userDirectory = __DIR__ . '/state/uploads/' . (int)$access['user_id'];
    if (!is_dir($userDirectory) && !mkdir($userDirectory, 0750, true) && !is_dir($userDirectory)) {
        ananke_respond(500, ['error' => 'upload_directory_unavailable']);
    }
    $safeName = bin2hex(random_bytes(16)) . ($extension !== '' ? '.' . $extension : '');
    $destination = $userDirectory . '/' . $safeName;
    if (!move_uploaded_file($temporary, $destination)) {
        ananke_respond(500, ['error' => 'upload_move_failed']);
    }
    chmod($destination, 0640);
    $objective = trim((string)($_POST['objective'] ?? 'general'));
    if ($objective === '' || strlen($objective) > 120) {
        @unlink($destination);
        ananke_respond(400, ['error' => 'invalid_objective']);
    }
    ananke_run_python([
        'action' => 'learning_analyze',
        'path' => $destination,
        'filename' => $originalName,
        'objective' => $objective,
        'user_id' => (int)$access['user_id'],
    ], 1200);
}

function ananke_run_python(array $payload, int $timeoutSeconds): never
{
    if (!function_exists('proc_open')) {
        ananke_respond(500, ['error' => 'proc_open_unavailable']);
    }

    $statePath = getenv('ANANKE_STATE_PATH') ?: (__DIR__ . '/state/ananke.sqlite3');
    $runtimePath = __DIR__ . '/Ananke_runtime.py';
    if (!is_file($runtimePath)) {
        ananke_respond(500, [
            'error' => 'ananke_runtime_missing',
            'detail' => 'Le fichier Ananke_runtime.py est absent.',
        ]);
    }

    $input = json_encode(
        $payload,
        JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR
    );

    $python = trim((string)(getenv('ANANKE_PYTHON_BIN') ?: 'python3'));
    if ($python === '') {
        $python = 'python3';
    }

    $result = ananke_execute_python_script(
        $python,
        $runtimePath,
        $statePath,
        $input,
        $timeoutSeconds
    );

    $decoded = json_decode($result['stdout'], true);
    if (!is_array($decoded)) {
        ananke_runtime_log('Réponse Python invalide', [[
            'command' => $result['command'],
            'exit_code' => $result['exit_code'],
            'stderr' => substr(trim($result['stderr']), 0, 2000),
            'stdout' => substr(trim($result['stdout']), 0, 1000),
        ]]);
        ananke_respond(500, [
            'error' => 'invalid_python_response',
            'detail' => trim($result['stderr']),
            'exit_code' => $result['exit_code'],
        ]);
    }

    if (isset($decoded['error'])) {
        $status = $result['exit_code'] === 0 ? 400 : 500;
        ananke_respond($status, $decoded);
    }

    ananke_respond(200, $decoded);
}

function ananke_execute_python_script(
    string $python,
    string $runtimePath,
    string $statePath,
    string $input,
    int $timeoutSeconds
): array {
    /*
     * Même contrat d'exécution que les workers Python déjà fonctionnels
     * dans Cercle : ``python3 /chemin/script.py --arguments``.
     * Tous les fragments sont échappés avant passage au shell.
     */
    $command = escapeshellarg($python)
        . ' ' . escapeshellarg($runtimePath)
        . ' --state ' . escapeshellarg($statePath);

    $descriptors = [
        0 => ['pipe', 'r'],
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ];

    $environment = getenv();
    if (!is_array($environment)) {
        $environment = [];
    }
    $environment['ANANKE_STATE_PATH'] = $statePath;
    $environment['PYTHONIOENCODING'] = 'utf-8';
    $environment['PYTHONUNBUFFERED'] = '1';
    $environment['PYTHONPATH'] = __DIR__;

    $pipes = [];
    try {
        $process = proc_open(
            $command,
            $descriptors,
            $pipes,
            __DIR__,
            $environment
        );
    } catch (Throwable $exception) {
        ananke_runtime_log('Impossible de lancer Ananke_runtime.py', [[
            'command' => $command,
            'exception' => $exception->getMessage(),
        ]]);
        ananke_respond(500, [
            'error' => 'python_launch_failed',
            'detail' => $exception->getMessage(),
        ]);
    }

    if (!is_resource($process)) {
        ananke_runtime_log('proc_open n’a pas démarré Ananke_runtime.py', [[
            'command' => $command,
        ]]);
        ananke_respond(500, [
            'error' => 'python_launch_failed',
            'detail' => 'proc_open n’a pas démarré le processus Python.',
        ]);
    }

    fwrite($pipes[0], $input);
    fclose($pipes[0]);
    stream_set_blocking($pipes[1], false);
    stream_set_blocking($pipes[2], false);

    $stdout = '';
    $stderr = '';
    $started = microtime(true);
    $lastStatus = null;

    while (true) {
        $stdout .= stream_get_contents($pipes[1]);
        $stderr .= stream_get_contents($pipes[2]);
        $lastStatus = proc_get_status($process);

        if (!$lastStatus['running']) {
            break;
        }
        if ((microtime(true) - $started) > $timeoutSeconds) {
            proc_terminate($process, 9);
            fclose($pipes[1]);
            fclose($pipes[2]);
            proc_close($process);
            ananke_runtime_log('Timeout du runtime Python', [[
                'command' => $command,
                'timeout_seconds' => $timeoutSeconds,
            ]]);
            ananke_respond(504, ['error' => 'ananke_runtime_timeout']);
        }
        usleep(20000);
    }

    $stdout .= stream_get_contents($pipes[1]);
    $stderr .= stream_get_contents($pipes[2]);
    fclose($pipes[1]);
    fclose($pipes[2]);

    $closeCode = proc_close($process);
    $exitCode = is_array($lastStatus)
        && isset($lastStatus['exitcode'])
        && (int)$lastStatus['exitcode'] >= 0
            ? (int)$lastStatus['exitcode']
            : (int)$closeCode;

    if ($exitCode !== 0) {
        ananke_runtime_log('Runtime Python terminé en erreur', [[
            'command' => $command,
            'exit_code' => $exitCode,
            'stderr' => substr(trim($stderr), 0, 4000),
        ]]);
    }

    return [
        'command' => $command,
        'stdout' => $stdout,
        'stderr' => $stderr,
        'exit_code' => $exitCode,
    ];
}

function ananke_runtime_log(string $message, array $context = []): void
{
    $line = date('[Y-m-d H:i:s] ') . $message;
    if ($context !== []) {
        $line .= ' ' . json_encode($context, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
    $line .= PHP_EOL;
    @file_put_contents(__DIR__ . '/state/ananke_runtime.log', $line, FILE_APPEND | LOCK_EX);
}

function ananke_respond(int $status, array $payload): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}
