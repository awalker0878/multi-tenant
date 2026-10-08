<?php

declare(strict_types=1);

return [
    // Internal service address/trust only. External OIDC settings belong to Governance data.
    'governance_url' => env('GOVERNANCE_URL'),
    'credential_file' => env('CONSOLE_CREDENTIAL_FILE'),
    'ca_file' => env('GOVERNANCE_CA_FILE'),
];
