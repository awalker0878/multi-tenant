<?php

declare(strict_types=1);

return [
    'name' => 'Enterprise Workload Mobility and Secure Hosting',
    'env' => env('APP_ENV', 'production'),
    'debug' => false,
    'url' => env('APP_URL', 'http://127.0.0.1:8000'),
    'timezone' => 'UTC',
    'locale' => 'en',
    'fallback_locale' => 'en',
    'cipher' => 'AES-256-CBC',
    'key' => env('APP_KEY'),
    'maintenance' => ['driver' => 'file'],
];
