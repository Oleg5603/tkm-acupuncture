<?php
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'method_not_allowed']);
    exit;
}

if ((int) ($_SERVER['CONTENT_LENGTH'] ?? 0) > 4096) {
    http_response_code(413);
    echo json_encode(['ok' => false, 'error' => 'payload_too_large']);
    exit;
}

$email = isset($_POST['email']) ? trim($_POST['email']) : '';

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'invalid_email']);
    exit;
}

$dir = getenv('TKM_PRIVATE_DATA_DIR');
if ($dir === false || trim($dir) === '') {
    http_response_code(503);
    echo json_encode(['ok' => false, 'error' => 'storage_not_configured']);
    exit;
}

if (!is_dir($dir) && !mkdir($dir, 0700, true)) {
    http_response_code(503);
    echo json_encode(['ok' => false, 'error' => 'storage_unavailable']);
    exit;
}

$orderId = bin2hex(random_bytes(12));
$file = rtrim($dir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . 'orders.jsonl';
$record = json_encode([
    'created_at' => gmdate('c'),
    'order_id' => $orderId,
    'email' => $email,
    'status' => 'pending_payment',
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;

$written = file_put_contents($file, $record, FILE_APPEND | LOCK_EX);
if ($written === false || $written !== strlen($record)) {
    http_response_code(503);
    echo json_encode(['ok' => false, 'error' => 'write_failed']);
    exit;
}

echo json_encode(['ok' => true, 'order_id' => $orderId]);
