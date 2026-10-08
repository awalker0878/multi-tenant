<?php

declare(strict_types=1);

use App\Application\Identity\Actions\BootstrapAdministrator;
use App\Application\Identity\Contracts\DeploymentTerminal;
use App\Domain\Identity\BootstrapAdministrator as Administrator;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;

beforeEach(function (): void {
    initializeIdentityFixture($this);
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

it('generates one high entropy credential and never redisplays or resets it on retry', function (): void {
    expect($this->temporary)->toMatch('/\A[0-9a-f]{48}\z/');
    $administrator = Administrator::query()->findOrFail(1);
    expect(Hash::check($this->temporary, $administrator->password_hash))->toBeTrue()
        ->and($administrator->state)->toBe('password_change_required')
        ->and($administrator->toArray())->not->toHaveKey('password_hash')
        ->and(app(BootstrapAdministrator::class)->handle())->toBeNull();
    expect(DB::table('app.identity_audit')->count())->toBe(1)
        ->and(DB::table('app.identity_outbox')->count())->toBe(1);
    $persisted = json_encode([
        DB::table('app.bootstrap_administrator')->first(), DB::table('app.identity_sessions')->get(),
        DB::table('app.identity_audit')->get(), DB::table('app.identity_outbox')->get(),
    ]);
    expect($persisted)->not->toContain($this->temporary);
});

it('requires independent mounted console identity and rejects health credentials', function (): void {
    $this->withHeader('Authorization', 'Bearer synthetic-health-token-0000000000000000')
        ->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => $this->temporary])
        ->assertUnauthorized()->assertJsonPath('error', 'invalid_workload_identity');
    expect(DB::table('app.identity_sessions')->count())->toBe(0);
    file_put_contents($this->credentialFile, bin2hex(random_bytes(32)));
    $this->withHeader('Authorization', 'Bearer '.$this->workload)->getJson('/identity/setup')->assertUnauthorized();
    unlink($this->credentialFile);
    $this->getJson('/identity/setup')->assertUnauthorized();
    file_put_contents($this->credentialFile, $this->workload);
});

it('enforces first-login restrictions in direct APIs then rotates all sessions on password change', function (): void {
    $first = localLogin($this);
    $second = localLogin($this);
    $this->withHeader('X-Console-Session', $first)->getJson('/identity/setup')->assertForbidden()->assertJsonPath('error', 'password_change_required');
    $this->getJson('/identity/session')->assertOk()->assertJsonPath('identity.permissions', ['identity.password.change', 'identity.logout']);
    $new = changeLocalPassword($this, $first);
    expect($new)->not->toBe($first);
    foreach ([$first, $second] as $old) {
        $this->withHeader('X-Console-Session', $old)->getJson('/identity/setup')->assertUnauthorized();
    }
    $this->withHeader('X-Console-Session', $new)->getJson('/identity/setup')->assertOk()->assertJsonPath('identity.permissions', ['identity.setup', 'identity.password.change', 'identity.logout']);
    $this->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => $this->temporary])->assertUnauthorized();
    localLogin($this, 'a different long password');
    expect(DB::table('app.identity_sessions')->where('token_hash', hash('sha256', $new))->exists())->toBeTrue()
        ->and(DB::table('app.identity_sessions')->where('token_hash', $new)->exists())->toBeFalse();
});

it('requires the current password and rejects reuse, short or mismatched new passwords', function (): void {
    $token = localLogin($this);
    $this->withHeader('X-Console-Session', $token);
    foreach ([
        [$this->temporary, $this->temporary, $this->temporary, 422],
        ['wrong current password', 'a different long password', 'a different long password', 401],
        [$this->temporary, 'too short', 'too short', 422],
        [$this->temporary, 'a different long password', 'a second different password', 422],
    ] as [$current, $password, $confirmation, $status]) {
        $this->postJson('/identity/password', ['current_password' => $current, 'password' => $password, 'password_confirmation' => $confirmation])->assertStatus($status);
    }
    expect(Administrator::query()->findOrFail(1)->state)->toBe('password_change_required');
    $this->getJson('/identity/setup')->assertForbidden();
});

it('expires temporary sessions and invalidates an explicitly logged out session', function (): void {
    $expired = localLogin($this);
    $this->travel(11)->minutes();
    $this->withHeader('X-Console-Session', $expired)->getJson('/identity/session')->assertUnauthorized();
    $this->travelBack();
    $token = localLogin($this);
    $this->withHeader('X-Console-Session', $token)->postJson('/identity/logout')->assertOk();
    $this->getJson('/identity/session')->assertUnauthorized();
    $this->postJson('/identity/logout')->assertOk();
    expect(DB::table('app.identity_audit')->where('event', 'identity.session.revoked')->count())->toBe(1);
});

it('commits throttling across requests and denies attempts during the lock window', function (): void {
    for ($i = 0; $i < 5; $i++) {
        $this->postJson('/identity/local-sessions', ['username' => $i % 2 ? 'admin' : 'guessed', 'password' => 'incorrect-password'])->assertUnauthorized();
    }
    $this->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => $this->temporary])->assertStatus(429)->assertHeader('Retry-After', '60');
    expect(DB::table('app.identity_audit')->where('event', 'identity.login.denied')->count())->toBe(5);
    $this->travel(61)->seconds();
    localLogin($this);
});

it('never recreates a retired identity and rejects its existing session even without a revocation row', function (): void {
    $token = changeLocalPassword($this, localLogin($this));
    // Seed the terminal lifecycle state; federated verification/activation is a later slice.
    Administrator::query()->findOrFail(1)->forceFill(['state' => 'retired', 'retired_at' => now(), 'password_hash' => null])->save();
    $this->withHeader('X-Console-Session', $token)->getJson('/identity/setup')->assertUnauthorized();
    $this->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => 'a different long password'])->assertUnauthorized();
    expect(app(BootstrapAdministrator::class)->handle())->toBeNull();
    DB::purge('identity_test');
    // A new connection/restart check uses persisted PostgreSQL in its CI campaign.
});

it('rolls back identity and audit together when outbox persistence fails', function (): void {
    Administrator::query()->findOrFail(1)->forceFill(['state' => 'uninitialized', 'password_hash' => null, 'credential_version' => 0])->save();
    DB::statement('DROP TABLE app.identity_outbox');
    $count = DB::table('app.identity_audit')->count();
    expect(fn () => app(BootstrapAdministrator::class)->handle())->toThrow(QueryException::class);
    expect(Administrator::query()->findOrFail(1)->state)->toBe('uninitialized')
        ->and(DB::table('app.identity_audit')->count())->toBe($count);
});

it('refuses bootstrap through redirected or noninteractive command output before mutation', function (): void {
    $terminal = Mockery::mock(DeploymentTerminal::class);
    $terminal->shouldReceive('isInteractive')->andReturn(false);
    $terminal->shouldNotReceive('display');
    $this->app->instance(DeploymentTerminal::class, $terminal);
    $this->artisan('identity:bootstrap', ['--console-url' => 'https://console.example.test'])->assertFailed();
    expect(DB::table('app.identity_audit')->count())->toBe(1);
});
