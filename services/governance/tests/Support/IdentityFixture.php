<?php

declare(strict_types=1);

use App\Application\Identity\Actions\BootstrapAdministrator;
use Illuminate\Support\Facades\DB;

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
            $sql = str_replace('identity_sessions_expiry ON app.identity_sessions', 'app.identity_sessions_expiry ON identity_sessions', $sql);
            $sql = str_replace('REFERENCES app.', 'REFERENCES ', $sql);
        }
        DB::unprepared($sql);
    }
    $test->credentialFile = tempnam(sys_get_temp_dir(), 'p02-console-');
    $test->workload = bin2hex(random_bytes(32));
    file_put_contents($test->credentialFile, $test->workload);
    chmod($test->credentialFile, 0600);
    config(['identity.console_credential_file' => $test->credentialFile]);
    $test->withHeader('Authorization', 'Bearer '.$test->workload);
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
