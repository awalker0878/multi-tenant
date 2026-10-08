<?php

declare(strict_types=1);

return [
    'host' => env('CONSOLE_BROKER_HOST'),
    'port' => env('CONSOLE_BROKER_PORT', 5671),
    'password_file' => env('CONSOLE_BROKER_PASSWORD_FILE'),
    'ca_file' => env('CONSOLE_BROKER_CA_FILE'),
];
