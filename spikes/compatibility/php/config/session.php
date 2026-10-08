<?php

declare(strict_types=1);

return [
    'driver' => env('SESSION_DRIVER', 'file'),
    'lifetime' => 30,
    'expire_on_close' => true,
    'encrypt' => false,
    'files' => storage_path('framework/sessions'),
    'connection' => null,
    'table' => 'sessions',
    'store' => null,
    'lottery' => [2, 100],
    'cookie' => 'p00_compatibility_session',
    'path' => '/',
    'domain' => null,
    'secure' => false,
    'http_only' => true,
    'same_site' => 'lax',
    'partitioned' => false,
    'serialization' => 'json',
];
