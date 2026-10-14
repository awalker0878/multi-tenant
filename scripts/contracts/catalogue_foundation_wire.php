<?php

declare(strict_types=1);

// Exercise Catalogue's current event encoder and decoder, not a fixture-only
// serialization check. Planning's installed consumer runs in the next process.
require dirname(__DIR__, 2).'/services/catalogue/vendor/autoload.php';

use App\Infrastructure\Messaging\EventCodec;
use App\Infrastructure\Messaging\GeneratedEvent;

$event = new GeneratedEvent(
    'catalogue.foundation.recorded',
    1,
    '10000000-0000-4000-8000-000000000001',
    '10000000-0000-4000-8000-000000000002',
    'tenant_a', 'actor_a', 'record_a', '1',
    str_repeat('a', 64), str_repeat('b', 40),
    '2026-10-08T00:00:00Z',
);
$codec = new EventCodec;
$wire = $codec->canonical($event);
if ($codec->decode($wire) != $event) {
    throw new RuntimeException('Catalogue emitted an event rejected by its own codec');
}
fwrite(STDOUT, $wire);
