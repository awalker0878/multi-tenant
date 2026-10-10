<?php

declare(strict_types=1);

return [
    'credential_file' => env('PLANNING_CALLER_CREDENTIAL_FILE'),
    'governance_url' => env('GOVERNANCE_URL'),
    'governance_credential_file' => env('GOVERNANCE_CREDENTIAL_FILE'),
    'ca_file' => env('GOVERNANCE_CA_FILE'),
    'migration_support_registry_file' => env('ASSURANCE_MIGRATION_SUPPORT_REGISTRY_FILE'),
    'qualification_runtime_file' => env('ASSURANCE_QUALIFICATION_RUNTIME_FILE'),
    'qualification_trust_file' => env('ASSURANCE_QUALIFICATION_TRUST_FILE'),
    'qualification_registry_file' => env('ASSURANCE_QUALIFICATION_REGISTRY_FILE'),
    'qualification_authority_mode' => env('ASSURANCE_QUALIFICATION_AUTHORITY_MODE', 'mounted'),
    'qualification_reviewer_credential_file' => env('ASSURANCE_PUBLICATION_REVIEWER_CREDENTIAL_FILE'),
    'qualification_observer_credential_file' => env('ASSURANCE_PUBLICATION_OBSERVER_CREDENTIAL_FILE'),
    'qualification_invalidation_url' => env('ASSURANCE_INVALIDATION_SINK_URL'),
    'qualification_invalidation_ca_file' => env('ASSURANCE_INVALIDATION_CA_FILE'),
    'qualification_invalidation_credential_file' => env('ASSURANCE_INVALIDATION_CREDENTIAL_FILE'),
];
