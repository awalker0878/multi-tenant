<?php

declare(strict_types=1);

return [
    // Workload trust is deployment-owned. OIDC provider settings are application data.
    'admission_file' => env('GOVERNANCE_IDENTITY_ADMISSION_FILE'),
    'recovery_trust_file' => env('GOVERNANCE_IDENTITY_RECOVERY_TRUST_FILE'),
    'console_credential_file' => env('CONSOLE_CREDENTIAL_FILE'),
    'service_credentials' => [
        'catalogue' => env('CATALOGUE_GOVERNANCE_CREDENTIAL_FILE'),
        'inventory' => env('INVENTORY_GOVERNANCE_CREDENTIAL_FILE'),
        'planning' => env('PLANNING_GOVERNANCE_CREDENTIAL_FILE'),
        'assurance' => env('ASSURANCE_GOVERNANCE_CREDENTIAL_FILE'),
    ],
    'session_minutes' => 30,
    'change_session_minutes' => 10,
    'max_attempts' => 5,
    'lock_seconds' => 60,
];
