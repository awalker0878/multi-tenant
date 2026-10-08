<?php

declare(strict_types=1);

return [
    'host' => env('GOVERNANCE_BROKER_HOST'),
    'port' => env('GOVERNANCE_BROKER_PORT', 5671),
    'password_file' => env('GOVERNANCE_BROKER_PASSWORD_FILE'),
    'ca_file' => env('GOVERNANCE_BROKER_CA_FILE'),
];
