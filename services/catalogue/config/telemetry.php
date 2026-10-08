<?php

declare(strict_types=1);

return [
    'enabled' => env('TELEMETRY_ENABLED', '0') === '1',
    'source_revision' => env('SOURCE_REVISION'),
    'environment' => env('TELEMETRY_ENVIRONMENT'),
];
