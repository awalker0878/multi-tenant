<?php

declare(strict_types=1);

use App\Application\Support\Contracts\SupportTrust;
use Illuminate\Support\Facades\DB;
use Symfony\Component\Process\Process;

beforeEach(function (): void {
    if (getenv('P02_TEST_POSTGRES') !== '1') {
        $this->markTestSkipped('Real PostgreSQL concurrency campaign only.');
    }
    initializeSupportFixture($this);
    $this->supportProcess = function (array $request, string $operation, string $token, array $body): Process {
        $process = new Process([PHP_BINARY, '-c', php_ini_loaded_file(), base_path('../../scripts/p02/support_process.php')], base_path(), [
            'DB_HOST' => '127.0.0.1', 'DB_PORT' => getenv('P02_TEST_PORT') ?: '5432',
            'DB_DATABASE' => 'p02_identity_test', 'DB_USERNAME' => 'postgres', 'DB_PASSWORD' => getenv('P02_TEST_PASSWORD'),
            'DB_SSLMODE' => 'prefer', 'APP_ENV' => 'testing', 'APP_KEY' => config('app.key'),
        ]);
        $process->setInput(json_encode(['token' => $token, 'tenant' => $this->tenant, 'id' => $request['id'], 'operation' => $operation,
            'key' => bin2hex(random_bytes(16)), 'body' => $body, 'admission_file' => $this->admissionFile,
            'credential_file' => $this->credentialFile, 'trust' => app(SupportTrust::class)->current()]));
        $process->setTimeout(20);

        return $process;
    };
});

afterEach(function (): void {
    if (isset($this->credentialFile)) {
        unlink($this->credentialFile);
    }
});

it('serializes independent approval races and requires the losing actor to review the current revision', function (): void {
    $request = createSupportRequest($this);
    $body = ['revision' => $request['revision'], 'binding_sha256' => $request['binding_sha256']];
    $one = ($this->supportProcess)($request, 'approve', $this->owner, $body + ['role' => 'tenant']);
    $two = ($this->supportProcess)($request, 'approve', $this->security, $body + ['role' => 'security']);
    $one->start();
    $two->start();
    $one->wait();
    $two->wait();
    $results = [trim($one->getOutput()), trim($two->getOutput())];
    sort($results);
    expect($one->getExitCode())->toBe(0)->and($two->getExitCode())->toBe(0)->and($results)->toBe(['committed', 'revision_conflict'])
        ->and(DB::table('app.support_approvals')->count())->toBe(1)
        ->and(DB::table('app.support_requests')->value('state'))->toBe('requested')
        ->and(DB::table('app.support_audit')->where('event', 'support.access.approved')->count())->toBe(1)
        ->and(DB::table('app.support_audit')->where('event', 'support.access.denied')->count())->toBe(1);
});

it('rechecks authority after waiting on a concurrent revocation instead of returning stale diagnostics', function (): void {
    $request = activateSupportRequest($this);
    $process = ($this->supportProcess)($request, 'inspect', $this->executor, $this->scope + [
        'binding_sha256' => $request['binding_sha256'], 'action' => 'support.membership.inspect', 'resource_id' => $this->targetMembership['id']]);
    DB::beginTransaction();
    try {
        DB::table('app.bootstrap_administrator')->where('id', 1)->lockForUpdate()->first();
        $process->start();
        $deadline = microtime(true) + 5;
        do {
            $waiting = DB::selectOne("SELECT count(*) AS count FROM pg_stat_activity WHERE datname = 'p02_identity_test' AND pid <> pg_backend_pid() AND wait_event_type = 'Lock'")->count;
            if ($waiting > 0 || microtime(true) > $deadline || ! $process->isRunning()) {
                break;
            }
            usleep(10000);
        } while (true);
        expect((int) $waiting)->toBeGreaterThan(0);
        // The same allowed columns and common owner lock used by security revocation.
        DB::table('app.support_security_grants')->where('id', $this->securityGrant['id'])->update(['revoked_at' => now(), 'revision' => 2]);
        DB::commit();
    } finally {
        if (DB::transactionLevel() > 0) {
            DB::rollBack();
        }
    }
    $process->wait();
    expect($process->getExitCode())->toBe(0)->and(trim($process->getOutput()))->toBe('support_authority_changed')
        ->and(DB::table('app.support_requests')->value('state'))->toBe('invalidated')
        ->and(DB::table('app.support_requests')->value('admission_count'))->toBe(0)
        ->and(DB::table('app.support_audit')->where('event', 'support.access.admitted')->count())->toBe(0);
});
