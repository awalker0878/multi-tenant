<?php

declare(strict_types=1);

return [
    // Workload trust is deployment-owned. OIDC provider settings are application data.
    'console_credential_file' => env('CONSOLE_CREDENTIAL_FILE'),
    'session_minutes' => 30,
    'change_session_minutes' => 10,
    'max_attempts' => 5,
    'lock_seconds' => 60,
];
