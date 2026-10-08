<?php

declare(strict_types=1);

use App\Infrastructure\Foundation\MountedSecret;

return [
    'default' => 'pgsql',
    'connections' => [
        'pgsql' => [
            'driver' => 'pgsql',
            'host' => env('DB_HOST'),
            'port' => env('DB_PORT', '5432'),
            'database' => env('DB_DATABASE'),
            'username' => env('DB_USERNAME'),
            'password' => (new MountedSecret)->read(env('DB_PASSWORD_FILE')) ?? '',
            'charset' => 'utf8',
            'prefix' => '',
            'prefix_indexes' => true,
            'search_path' => 'public',
            'sslmode' => env('DB_SSLMODE', 'verify-full'),
            'sslrootcert' => env('DB_SSLROOTCERT'),
        ],
    ],
];
