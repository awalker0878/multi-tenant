<?php

declare(strict_types=1);

use App\Application\Identity\Actions\BootstrapAdministrator;
use App\Application\Identity\Contracts\OidcHttpTransport;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Testing\TestResponse;
use Tests\Support\SyntheticOidcTransport;

function initializeIdentityFixture(object $test): void
{
    // This suite reuses the exact schema statements; PostgreSQL runs separately in CI.
    // Only the explicit disposable test database may use the PostgreSQL branch.
    if (getenv('P02_TEST_POSTGRES') === '1') {
        config(['database.connections.identity_test' => [
            'driver' => 'pgsql', 'host' => '127.0.0.1', 'port' => getenv('P02_TEST_PORT') ?: '5432',
            'database' => 'p02_identity_test', 'username' => 'postgres',
            'password' => getenv('P02_TEST_PASSWORD'), 'charset' => 'utf8', 'prefix' => '', 'sslmode' => 'prefer',
        ]]);
    } else {
        config(['database.connections.identity_test' => ['driver' => 'sqlite', 'database' => ':memory:', 'prefix' => '', 'foreign_key_constraints' => true]]);
    }
    config(['database.default' => 'identity_test', 'hashing.argon.memory' => 1024, 'hashing.argon.time' => 1]);
    DB::purge('identity_test');
    if (DB::getDriverName() === 'pgsql') {
        DB::unprepared('DROP SCHEMA IF EXISTS app CASCADE; CREATE SCHEMA app');
    } else {
        DB::statement("ATTACH DATABASE ':memory:' AS app");
    }
    foreach (glob(database_path('migrations/*.sql')) as $migration) {
        $sql = file_get_contents($migration);
        $sql = preg_replace('/^\\\\.*$/m', '', $sql);
        $sql = preg_replace('/^(?:SET LOCAL ROLE|GRANT|REVOKE) [^;]+;\s*/m', '', $sql);
        if (DB::getDriverName() === 'sqlite') {
            // SQLite cannot replace CHECK constraints; materialize the post-012 shape.
            // The actual additive constraint migration and replay run on PostgreSQL.
            if (basename($migration) === '006_actor_delegation.sql') {
                $sql = str_replace("'catalogue', 'planning', 'assurance'", "'catalogue', 'inventory', 'planning', 'assurance'", $sql);
            }
            if (basename($migration) === '012_inventory_delegation.sql') {
                continue;
            }
            // Real owner/function privileges are exercised on PostgreSQL, never inferred here.
            $sql = preg_replace('/-- BEGIN POSTGRES RECOVERY FUNCTION.*?-- END POSTGRES RECOVERY FUNCTION/s', '', $sql);
            $sql = str_replace('identity_sessions_expiry ON app.identity_sessions', 'app.identity_sessions_expiry ON identity_sessions', $sql);
            $sql = str_replace('REFERENCES app.', 'REFERENCES ', $sql);
            // SQLite cannot DROP NOT NULL; materialize the post-005 audit shape.
            if (basename($migration) === '003_tenancy.sql') {
                $sql = preg_replace('/(CREATE TABLE IF NOT EXISTS app\.governance_audit \(.*?actor_id uuid) NOT NULL/s', '$1', $sql);
            }
            $sql = str_replace('ALTER TABLE app.governance_audit ALTER COLUMN actor_id DROP NOT NULL;', '', $sql);
            $sql = str_replace('ADD COLUMN IF NOT EXISTS', 'ADD COLUMN', $sql);
            $sql = str_replace('governance_outbox_pending ON app.governance_outbox', 'app.governance_outbox_pending ON governance_outbox', $sql);
            $sql = str_replace('identity_outbox_pending ON app.identity_outbox', 'app.identity_outbox_pending ON identity_outbox', $sql);
            $sql = str_replace('approvals_expiry ON app.approvals', 'app.approvals_expiry ON approvals', $sql);
            $sql = str_replace('membership_directory_position ON app.tenant_memberships', 'app.membership_directory_position ON tenant_memberships', $sql);
            $sql = str_replace('actor_directory_position ON app.tenant_memberships', 'app.actor_directory_position ON tenant_memberships', $sql);
            $sql = preg_replace('/CREATE INDEX IF NOT EXISTS (support_[a-z_]+) ON app\.([a-z_]+)/', 'CREATE INDEX IF NOT EXISTS app.$1 ON $2', $sql);
        }
        DB::unprepared($sql);
    }
    $test->credentialFile = tempnam(sys_get_temp_dir(), 'p02-console-');
    $test->workload = bin2hex(random_bytes(32));
    file_put_contents($test->credentialFile, $test->workload);
    chmod($test->credentialFile, 0600);
    config(['identity.console_credential_file' => $test->credentialFile]);
    $test->withHeader('Authorization', 'Bearer '.$test->workload);
    $test->admissionFile = tempnam(sys_get_temp_dir(), 'p02-admission-');
    $test->admission = ['version' => 1, 'installation_id' => (string) Str::uuid(), 'epoch' => bin2hex(random_bytes(32)), 'state' => 'active', 'bootstrap_allowed' => true];
    file_put_contents($test->admissionFile, json_encode($test->admission));
    chmod($test->admissionFile, 0600);
    config(['identity.admission_file' => $test->admissionFile]);
    $test->temporary = app(BootstrapAdministrator::class)->handle();
}

function localLogin(object $test, ?string $password = null): string
{
    return $test->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => $password ?? $test->temporary])
        ->assertOk()->assertHeader('Cache-Control', 'no-store, private')->json('session_token');
}

function changeLocalPassword(object $test, string $token, string $password = 'a different long password'): string
{
    return $test->withHeader('X-Console-Session', $token)->postJson('/identity/password', [
        'current_password' => $test->temporary, 'password' => $password, 'password_confirmation' => $password,
    ])->assertOk()->assertJsonPath('identity.password_change_required', false)->json('session_token');
}

function saveConnection(object $test, array $overrides = []): void
{
    $test->withHeader('X-Console-Session', $test->token)->putJson('/identity/oidc', array_replace($test->settings, $overrides))->assertCreated();
}
function beginFederation(object $test, string $purpose = 'setup', ?string $token = null): array
{
    $url = $test->withHeader('X-Console-Session', $token ?? $test->token)->postJson('/identity/oidc/flows', ['purpose' => $purpose, 'browser_binding' => $test->binding])
        ->assertOk()->json('authorization_url');

    return $test->provider->authorize($url) + ['browser_binding' => $test->binding];
}
function activateFederation(object $test): string
{
    saveConnection($test);
    $proof = $test->postJson('/identity/oidc/callback', beginFederation($test))->assertOk()->json('verification_token');

    return $test->postJson('/identity/oidc/activation', ['verification_token' => $proof])->assertOk()->assertJsonPath('identity.kind', 'federated')->json('session_token');
}

function initializeFederationFixture(object $test): void
{
    initializeIdentityFixture($test);
    $test->provider = new SyntheticOidcTransport;
    app()->instance(OidcHttpTransport::class, $test->provider);
    $test->token = changeLocalPassword($test, localLogin($test));
    $test->withHeader('X-Console-Session', $test->token);
    $test->settings = ['revision' => 0, 'issuer' => 'https://idp.example.test/realm', 'client_id' => 'console-client',
        'client_secret' => 'synthetic-oidc-secret', 'redirect_uri' => 'https://console.example.test/identity/callback',
        'administrator_subject' => 'immutable-admin-subject', 'private_networks' => []];
    $test->binding = bin2hex(random_bytes(32));
    $test->token = activateFederation($test);
    $test->withHeader('X-Console-Session', $test->token);
}

function federatedLogin(object $test, string $subject): string
{
    $test->provider->claims = ['sub' => $subject];
    $token = $test->postJson('/identity/oidc/callback', beginFederation($test, 'login', ''))->assertOk()->json('session_token');
    $test->provider->claims = [];

    return $token;
}

function tenantCommand(object $test, string $path, array $input, ?string $token = null, ?string $key = null): TestResponse
{
    return $test->withHeader('X-Console-Session', $token ?? $test->token)->withHeader('Idempotency-Key', $key ?? bin2hex(random_bytes(16)))
        ->postJson($path, $input);
}

function tenantMember(object $test, string $tenant, string $subject, string $role, array $scope = [], int $revision = 0, string $state = 'active'): array
{
    return tenantCommand($test, '/v1/tenants/'.$tenant.'/memberships', [
        'revision' => $revision, 'subject' => $subject, 'role' => $role, 'state' => $state,
        'site_id' => $scope['site_id'] ?? null, 'environment' => $scope['environment'] ?? null, 'expires_at' => null,
    ])->assertOk()->json();
}
