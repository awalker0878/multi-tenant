<?php

declare(strict_types=1);

return [
    'driver' => env('SESSION_DRIVER', 'database'),
    'lifetime' => 30,
    'expire_on_close' => true,
    'encrypt' => true,
    'files' => storage_path('framework/sessions'),
    'connection' => 'pgsql',
    'table' => 'app.sessions',
    'store' => null,
    'lottery' => [2, 100],
    'cookie' => 'console_session',
    'path' => '/',
    'domain' => null,
    'secure' => env('SESSION_SECURE_COOKIE', true),
    'http_only' => true,
    'same_site' => 'lax',
    'partitioned' => false,
    'serialization' => 'json',
];
