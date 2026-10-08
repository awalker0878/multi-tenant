<?php

declare(strict_types=1);

return [
    'producer_file' => env('LIFECYCLE_ASSURANCE_CREDENTIAL_FILE'),
    'console_file' => env('CONSOLE_ASSURANCE_CREDENTIAL_FILE'),
    'lifecycle_url' => env('LIFECYCLE_URL'), 'lifecycle_ca' => env('LIFECYCLE_CA_FILE'),
    'lifecycle_file' => env('ASSURANCE_LIFECYCLE_CREDENTIAL_FILE'),
    'simulator_url' => env('SIMULATOR_URL'), 'simulator_ca' => env('SIMULATOR_CA_FILE'),
    'simulator_file' => env('ASSURANCE_SIMULATOR_CREDENTIAL_FILE'),
    'governance_url' => env('GOVERNANCE_URL'), 'governance_ca' => env('GOVERNANCE_CA_FILE'),
    'governance_file' => env('ASSURANCE_GOVERNANCE_CREDENTIAL_FILE'),
];
