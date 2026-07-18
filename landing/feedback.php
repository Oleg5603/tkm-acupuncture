<?php
header('Content-Type: application/json; charset=utf-8');

$name    = isset($_POST['name'])    ? trim($_POST['name'])    : '';
$contact = isset($_POST['contact']) ? trim($_POST['contact']) : '';
$version = isset($_POST['version']) ? trim($_POST['version']) : '';
$message = isset($_POST['message']) ? trim($_POST['message']) : '';

$version = in_array($version, ['simple', 'pro'], true) ? $version : '';
$versionLabel = $version === 'pro' ? 'Профессиональная' : ($version === 'simple' ? 'Простая' : 'не указана');

if ($message === '' || mb_strlen($message) < 5) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'empty_message']);
    exit;
}

$dir = __DIR__ . '/ТКМ';
if (!is_dir($dir)) {
    mkdir($dir, 0755, true);
}

$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '';
$line = date('Y-m-d H:i:s') . "\t" . $name . "\t" . $contact . "\t" . $versionLabel . "\t" . $ip . "\t" . str_replace(["\r", "\n"], ' ', $message) . PHP_EOL;
file_put_contents($dir . '/feedback.txt', $line, FILE_APPEND | LOCK_EX);

$to      = 'ogp56@bk.ru';
$subject = '=?UTF-8?B?' . base64_encode('ТКМ — отзыв/рекомендация') . '?=';
$body    = "Версия: {$versionLabel}\n"
         . "Имя: {$name}\n"
         . "Контакт: {$contact}\n\n"
         . "Сообщение:\n{$message}\n";
$headers = "From: ТКМ лендинг <no-reply@tkm.ogp56bkn.beget.tech>\r\n"
         . "Content-Type: text/plain; charset=UTF-8\r\n";

@mail($to, $subject, $body, $headers);

echo json_encode(['ok' => true]);
