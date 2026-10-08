<?php

declare(strict_types=1);

return [
    'default' => env('CACHE_STORE', 'database'),
    'stores' => [
        'array' => ['driver' => 'array', 'serialize' => false],
        'database' => [
            'driver' => 'database',
            'connection' => 'pgsql',
            'table' => 'app.cache',
            'lock_connection' => 'pgsql',
            'lock_table' => 'app.cache_locks',
        ],
    ],
    'prefix' => 'console:',
];
