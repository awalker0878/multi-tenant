<?php

declare(strict_types=1);

// Mounted keys are loaded during configuration bootstrap; rotation requires a restart.
// If a path is explicitly supplied, an unreadable file must never fall back to APP_KEY.
$keyFile = env('APP_KEY_FILE');
$key = env('APP_KEY');
if ($keyFile !== null) {
    $key = null;
    if (is_string($keyFile) && str_starts_with($keyFile, '/') && ! str_contains($keyFile, "\0") && is_file($keyFile) && is_readable($keyFile)) {
        $contents = @file_get_contents($keyFile, false, null, 0, 4097);
        if (is_string($contents) && strlen($contents) <= 4096) {
            $key = rtrim($contents, "\r\n");
        }
    }
}

return [
    'name' => 'Assurance',
    'env' => env('APP_ENV', 'production'),
    'debug' => false,
    'url' => env('APP_URL', 'http://127.0.0.1:8000'),
    'timezone' => 'UTC',
    'locale' => 'en',
    'fallback_locale' => 'en',
    'cipher' => 'AES-256-CBC',
    'key' => $key,
    'maintenance' => ['driver' => 'file'],
];
