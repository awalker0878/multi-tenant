<?php

declare(strict_types=1);

return ['evidence_url' => env('ASSURANCE_URL'), 'evidence_ca' => env('ASSURANCE_CA_FILE'), 'evidence_file' => env('CONSOLE_ASSURANCE_CREDENTIAL_FILE'), 'url' => env('LIFECYCLE_URL'), 'credential_file' => env('CONSOLE_LIFECYCLE_CREDENTIAL_FILE'), 'ca_file' => env('LIFECYCLE_CA_FILE')];
