<?php
header('Content-Type: application/json; charset=utf-8');

$email = isset($_POST['email']) ? trim($_POST['email']) : '';

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'invalid_email']);
    exit;
}

// Папка "ТКМ" рядом со скриптом (создаётся при первом обращении)
$dir = __DIR__ . '/ТКМ';
if (!is_dir($dir)) {
    mkdir($dir, 0755, true);
}

$file = $dir . '/emails.txt';
$line = date('Y-m-d H:i:s') . "\t" . $email . "\t" . ($_SERVER['REMOTE_ADDR'] ?? '') . PHP_EOL;

file_put_contents($file, $line, FILE_APPEND | LOCK_EX);

echo json_encode(['ok' => true]);
