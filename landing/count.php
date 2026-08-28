<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

$type = isset($_GET['type']) ? $_GET['type'] : (isset($_POST['type']) ? $_POST['type'] : 'demo');
$type = in_array($type, ['demo', 'full'], true) ? $type : 'demo';

$file = __DIR__ . '/downloads_count_' . $type . '.txt';

if (!file_exists($file)) {
    file_put_contents($file, '0');
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $fp = fopen($file, 'c+');
    flock($fp, LOCK_EX);
    $count = (int) fread($fp, 1024);
    $count++;
    ftruncate($fp, 0);
    rewind($fp);
    fwrite($fp, (string) $count);
    flock($fp, LOCK_UN);
    fclose($fp);
    echo json_encode(['type' => $type, 'count' => $count]);
    exit;
}

$count = (int) file_get_contents($file);
echo json_encode(['type' => $type, 'count' => $count]);
