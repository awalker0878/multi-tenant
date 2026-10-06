<?php

declare(strict_types=1);

return ['broker_host' => env('CATALOGUE_BROKER_HOST'), 'broker_port' => env('CATALOGUE_BROKER_PORT', 5671), 'broker_password_file' => env('CATALOGUE_BROKER_PASSWORD_FILE'), 'broker_ca_file' => env('CATALOGUE_BROKER_CA_FILE')];
