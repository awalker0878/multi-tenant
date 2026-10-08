<?php

declare(strict_types=1);

use App\Infrastructure\Foundation\MountedSecret;

// One owned database and runtime identity. Missing settings fail authentication;
// credentials never fall back to a migrator, a URL, a socket or an administrator.
$host = env('DB_HOST', 'unconfigured.invalid');
$certificate = env('DB_SSLROOTCERT', '/run/secrets/ca.crt');
if (! is_string($host) || ! preg_match('/\A[A-Za-z0-9_.:-]{1,253}\z/', $host)
    || ! is_string($certificate) || ! preg_match('~\A/[A-Za-z0-9_./-]+\z~', $certificate)
    || env('DB_SSLMODE', 'verify-full') !== 'verify-full') {
    throw new RuntimeException('Invalid Console database configuration');
}

return [
    'default' => 'pgsql',
    'connections' => [
        'pgsql' => [
            'driver' => 'pgsql',
            'host' => $host,
            'port' => '5432',
            'database' => 'console',
            'username' => 'console_runtime',
            'password' => (new MountedSecret)->read(env('DB_PASSWORD_FILE')) ?? '',
            'charset' => 'utf8',
            'prefix' => '',
            'search_path' => 'app',
            'sslmode' => 'verify-full',
            'sslrootcert' => $certificate,
            'options' => [PDO::ATTR_TIMEOUT => 2],
        ],
    ],
];
