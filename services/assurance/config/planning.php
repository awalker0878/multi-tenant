<?php

declare(strict_types=1);

return [
    'credential_file' => env('PLANNING_CALLER_CREDENTIAL_FILE'),
    'governance_url' => env('GOVERNANCE_URL'),
    'governance_credential_file' => env('GOVERNANCE_CREDENTIAL_FILE'),
    'ca_file' => env('GOVERNANCE_CA_FILE'),
    'migration_support_registry_file' => env('ASSURANCE_MIGRATION_SUPPORT_REGISTRY_FILE'),
    'qualification_registry_file' => env('ASSURANCE_QUALIFICATION_REGISTRY_FILE'),
];
