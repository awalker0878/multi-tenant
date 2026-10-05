<?php

declare(strict_types=1);

require $argv[1].'/vendor/autoload.php';
$codec = new App\Infrastructure\Messaging\EventCodec;
$result = [];
foreach (json_decode(file_get_contents($argv[2]), true, flags: JSON_THROW_ON_ERROR) as $fixture) {
    try {
        $event = $codec->decode(json_encode($fixture['value'], JSON_THROW_ON_ERROR));
        $result[] = ['id' => $fixture['id'], 'valid' => true, 'sha256' => hash('sha256', $codec->canonical($event))];
    } catch (Throwable) {
        $result[] = ['id' => $fixture['id'], 'valid' => false];
    }
}
echo json_encode($result, JSON_THROW_ON_ERROR).PHP_EOL;
