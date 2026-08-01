<?php
declare(strict_types=1);

/**
 * Contrôle d'accès privé d'ANANKÉ.
 *
 * Contrat imposé par l'écosystème Cercle :
 * - la connexion MySQL est ouverte exclusivement par /html/oracle_connect.php ;
 * - oracle_connect.php expose $conn, créé par mysqli_connect() ;
 * - aucun PDO, aucun second jeu d'identifiants, aucun fallback de connexion.
 */

function ananke_load_oracle_connect(): mysqli
{
    $oraclePath = dirname(__DIR__, 2) . '/oracle_connect.php';

    if (!is_file($oraclePath)) {
        throw new RuntimeException('oracle_connect.php introuvable dans le dossier html.');
    }

    /** @var mixed $conn */
    $conn = null;
    require $oraclePath;

    if (!$conn instanceof mysqli) {
        throw new RuntimeException('oracle_connect.php doit exposer une connexion mysqli valide dans $conn.');
    }

    if (!mysqli_ping($conn)) {
        throw new RuntimeException('La connexion mysqli fournie par oracle_connect.php est inactive.');
    }

    return $conn;
}

function ananke_user_id(): ?int
{
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }

    // Compatibilité avec les conventions de session déjà rencontrées dans Cercle.
    foreach (['user_id', 'id_user', 'userid', 'id'] as $key) {
        if (
            isset($_SESSION[$key])
            && filter_var($_SESSION[$key], FILTER_VALIDATE_INT) !== false
            && (int)$_SESSION[$key] > 0
        ) {
            return (int)$_SESSION[$key];
        }
    }

    if (
        isset($_SESSION['user']['id'])
        && filter_var($_SESSION['user']['id'], FILTER_VALIDATE_INT) !== false
        && (int)$_SESSION['user']['id'] > 0
    ) {
        return (int)$_SESSION['user']['id'];
    }

    return null;
}

function ananke_access_context(): array
{
    $conn = ananke_load_oracle_connect();
    $userId = ananke_user_id();

    if ($userId === null) {
        return [
            'authenticated' => false,
            'granted' => false,
            'user_id' => null,
            'access' => 'denied',
        ];
    }

    $sql = 'SELECT id, ananke_access FROM users WHERE id = ? LIMIT 1';
    $statement = mysqli_prepare($conn, $sql);

    if ($statement === false) {
        throw new RuntimeException('Préparation SQL impossible : ' . mysqli_error($conn));
    }

    mysqli_stmt_bind_param($statement, 'i', $userId);

    if (!mysqli_stmt_execute($statement)) {
        $detail = mysqli_stmt_error($statement);
        mysqli_stmt_close($statement);
        throw new RuntimeException('Vérification de l’accès ANANKÉ impossible : ' . $detail);
    }

    mysqli_stmt_bind_result($statement, $resolvedId, $resolvedAccess);
    $found = mysqli_stmt_fetch($statement);
    mysqli_stmt_close($statement);

    if ($found !== true) {
        return [
            'authenticated' => false,
            'granted' => false,
            'user_id' => $userId,
            'access' => 'denied',
        ];
    }

    $access = strtolower(trim((string)$resolvedAccess));
    $granted = $access === 'granted';

    return [
        'authenticated' => true,
        'granted' => $granted,
        'user_id' => (int)$resolvedId,
        'access' => $granted ? 'granted' : 'denied',
    ];
}

function ananke_csrf_token(): string
{
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }

    if (empty($_SESSION['ananke_csrf']) || !is_string($_SESSION['ananke_csrf'])) {
        $_SESSION['ananke_csrf'] = bin2hex(random_bytes(32));
    }

    return $_SESSION['ananke_csrf'];
}

function ananke_require_csrf(): void
{
    $provided = (string)($_SERVER['HTTP_X_ANANKE_CSRF'] ?? '');
    $expected = ananke_csrf_token();

    if ($provided === '' || !hash_equals($expected, $provided)) {
        throw new RuntimeException('Jeton CSRF invalide.');
    }
}
