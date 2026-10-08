<?php

declare(strict_types=1);

return [
    // Internal owning-service address and workload trust, never external OIDC values.
    'planning_url' => env('PLANNING_URL'),
    'planning_credential_file' => env('PLANNING_CREDENTIAL_FILE'),
    'planning_ca_file' => env('PLANNING_CA_FILE'),
];
