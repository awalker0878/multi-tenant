<?php

declare(strict_types=1);

return [
    'health_token_file' => env('HEALTH_TOKEN_FILE'),
    'database' => [
        'host' => env('DB_HOST'),
        'port' => env('DB_PORT', '5432'),
        'database' => env('DB_DATABASE'),
        'username' => env('DB_USERNAME'),
        'password_file' => env('DB_PASSWORD_FILE'),
        'sslmode' => env('DB_SSLMODE', 'verify-full'),
        'sslrootcert' => env('DB_SSLROOTCERT'),
    ],
];
