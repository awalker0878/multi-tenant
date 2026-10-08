<?php

declare(strict_types=1);

it('loads the mounted database password and never falls back to an environment credential', function (string $mode): void {
    $previousEnv = $_ENV;
    $previousServer = $_SERVER;
    $path = tempnam(sys_get_temp_dir(), 'database-password-');
    $password = bin2hex(random_bytes(32));
    file_put_contents($path, $password."\n");
    $_ENV['DB_PASSWORD'] = $_SERVER['DB_PASSWORD'] = 'unused-environment-credential';
    $_ENV['DB_PASSWORD_FILE'] = $_SERVER['DB_PASSWORD_FILE'] = $path;

    try {
        $loaded = require base_path('config/database.php');
        expect($loaded['connections']['pgsql']['password'])->toBe($password);
        match ($mode) {
            'absent' => unlink($path),
            'empty' => file_put_contents($path, ''),
            'multiline' => file_put_contents($path, $password."\nextra"),
            'oversize' => file_put_contents($path, str_repeat('a', 4097)),
            'unconfigured' => $_ENV['DB_PASSWORD_FILE'] = $_SERVER['DB_PASSWORD_FILE'] = null,
            'wrapper' => $_ENV['DB_PASSWORD_FILE'] = $_SERVER['DB_PASSWORD_FILE'] = 'data://text/plain,'.$password,
        };
        $loaded = require base_path('config/database.php');
        expect($loaded['connections']['pgsql']['password'])->toBe('');
    } finally {
        $_ENV = $previousEnv;
        $_SERVER = $previousServer;
        if (is_file($path)) {
            unlink($path);
        }
    }
})->with(['absent', 'empty', 'multiline', 'oversize', 'unconfigured', 'wrapper']);
