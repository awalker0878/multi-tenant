<?php

declare(strict_types=1);

use App\Application\Recovery\Contracts\RecoveryDatabase;
use App\Domain\Recovery\RecoveryJson;
use App\Domain\Support\SupportTrustState;
use App\Infrastructure\Recovery\PostgresRecoveryDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

function recoveryTestKeys(): array
{
    static $keys;
    if ($keys === null) {
        $keys = [];
        foreach (['recovery_owner', 'security_reviewer'] as $role) {
            $private = openssl_pkey_new(['private_key_bits' => 3072, 'private_key_type' => OPENSSL_KEYTYPE_RSA]);
            $keys[] = ['private' => $private, 'principal' => ['id' => (string) Str::uuid(), 'role' => $role, 'public_key_pem' => openssl_pkey_get_details($private)['key']]];
        }
    }

    return $keys;
}

function initializeRecoveryFixture(object $test): void
{
    initializeSupportFixture($test);
    $test->activeSupport = activateSupportRequest($test);
    supportInspect($test, $test->activeSupport)->assertOk();
    // Nonempty restored authority fixtures exercise each reconciliation transition.
    DB::table('app.approvals')->insert(['id' => (string) Str::uuid(), 'tenant_id' => $test->tenant, 'plan_id' => (string) Str::uuid(),
        'plan_revision' => 1, 'plan_digest' => hash('sha256', 'synthetic-plan'), 'binding_json' => '{}',
        'requester_id' => $test->requesterId, 'request_authority' => hash('sha256', 'synthetic-authority'),
        'policy_version' => 1, 'state' => 'approved', 'revision' => 2, 'expires_at' => now()->addHour(), 'created_at' => now()]);
    DB::table('app.actor_delegations')->insert(['id' => (string) Str::uuid(), 'token_hash' => hash('sha256', 'synthetic-delegation'),
        'session_hash' => hash('sha256', $test->requester), 'tenant_id' => $test->tenant, 'actor_id' => $test->requesterId,
        'audience' => 'catalogue', 'action' => 'applications.inspect', 'scope_json' => '{}',
        'authority_fingerprint' => hash('sha256', 'synthetic-authority'), 'service_fingerprint' => hash('sha256', 'synthetic-service'),
        'console_fingerprint' => hash('sha256', $test->workload), 'created_at' => now(), 'expires_at' => now()->addMinute()]);
    beginFederation($test, 'login', '');
    if (DB::getDriverName() === 'pgsql') {
        DB::unprepared("DO \$do\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='governance_owner') THEN CREATE ROLE governance_owner NOLOGIN; END IF; END; \$do\$;");
        DB::unprepared('GRANT USAGE ON SCHEMA app TO governance_owner; GRANT ALL ON ALL TABLES IN SCHEMA app TO governance_owner;');
        app()->bind(RecoveryDatabase::class, PostgresRecoveryDatabase::class);
    } else {
        // Only pure recovery behavior is tested on SQLite. Real role/lock denial runs on PostgreSQL.
        app()->instance(RecoveryDatabase::class, new class implements RecoveryDatabase
        {
            public function observe(Closure $read): SupportTrustState
            {
                return $read();
            }

            public function lock(): void {}

            public function tables(): array
            {
                return array_map(fn (object $row): string => $row->name, DB::select("SELECT name FROM app.sqlite_master WHERE type='table' ORDER BY name"));
            }
        });
    }
    $test->recoveryKeys = recoveryTestKeys();
    $test->recoveryDirectory = sys_get_temp_dir().'/p02-recovery-'.bin2hex(random_bytes(8));
    mkdir($test->recoveryDirectory, 0700);
    $test->recoveryTrust = ['version' => 1, 'installation_id' => $test->admission['installation_id'],
        'valid_from' => now()->getTimestamp() - 60, 'valid_until' => now()->getTimestamp() + 3600,
        'principals' => array_column($test->recoveryKeys, 'principal')];
    $test->trustFile = $test->recoveryDirectory.'/trust.json';
    file_put_contents($test->trustFile, RecoveryJson::encode($test->recoveryTrust));
    chmod($test->trustFile, 0600);
    config(['identity.recovery_trust_file' => $test->trustFile]);
    $test->priorBinding = DB::table('app.identity_admission')->value('binding_sha256');
    $test->admission['state'] = 'held';
    $test->admission['bootstrap_allowed'] = false;
    $test->admission['epoch'] = bin2hex(random_bytes(32));
    file_put_contents($test->admissionFile, RecoveryJson::encode($test->admission));
    $test->previousWorkload = $test->workload;
    $test->workload = bin2hex(random_bytes(32));
    file_put_contents($test->credentialFile, $test->workload);
    $test->withHeader('Authorization', 'Bearer '.$test->workload);
    $test->ownerMembership = DB::table('app.tenant_memberships')->where('tenant_id', $test->tenant)->where('role', 'tenant_admin')->value('id');
    $test->observations = ['case_reference' => 'REC-100', 'restore_sha256' => hash('sha256', 'synthetic-restored-archive'),
        'records_sha256' => hash('sha256', 'synthetic-current-retirement-revocation-and-provider-records'),
        'containment_sha256' => hash('sha256', 'synthetic-infrastructure-containment-observations'),
        'previous_workloads' => ['console' => hash('sha256', $test->previousWorkload), 'catalogue' => null, 'inventory' => null, 'planning' => null, 'assurance' => null],
        'memberships' => [['id' => $test->ownerMembership, 'owner_record_sha256' => hash('sha256', 'synthetic-current-tenant-owner-decision')]]];
}

function recoveryEnvelope(object $test, array $payload): string
{
    $wire = RecoveryJson::encode($payload);
    $signatures = [];
    foreach ($test->recoveryKeys as $key) {
        openssl_sign(RecoveryJson::DOMAIN.$wire, $signature, $key['private'], OPENSSL_ALGO_SHA256);
        $signatures[] = ['principal_id' => $key['principal']['id'], 'signature' => base64_encode($signature)];
    }

    return RecoveryJson::encode(['payload' => base64_encode($wire), 'signatures' => $signatures]);
}
