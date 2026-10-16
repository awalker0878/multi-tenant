<?php

declare(strict_types=1);

use App\Domain\Identity\IdentityFailure;
use App\Infrastructure\Identity\GovernanceIdentityGateway;
use Illuminate\Http\Client\Request as OutboundRequest;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia as Assert;

beforeEach(function (): void {
    $this->credentialFile = tempnam(sys_get_temp_dir(), 'p02-console-');
    $this->workloadCredential = bin2hex(random_bytes(32));
    file_put_contents($this->credentialFile, $this->workloadCredential);
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $this->credentialFile]);
    Http::preventStrayRequests();
});

afterEach(function (): void {
    unlink($this->credentialFile);
});

function identityResponse(bool $changeRequired = true, string $token = ''): array
{
    return ['identity' => ['subject' => 'bootstrap-admin', 'password_change_required' => $changeRequired,
        'permissions' => $changeRequired ? ['identity.password.change', 'identity.logout'] : ['identity.setup', 'identity.password.change', 'identity.logout']],
        'session_token' => $token ?: str_repeat('a', 64), 'expires_at' => now()->addHour()->toIso8601String()];
}

it('validates exact federated identity and retains session expiry from the installed release', function (): void {
    $this->freezeTime();
    $identity = ['subject' => '550e8400-e29b-41d4-a716-446655440000', 'kind' => 'federated',
        'password_change_required' => false, 'permissions' => ['identity.logout']];
    Http::fake(['governance.example.test/identity/session' => Http::response(['identity' => $identity])]);
    $actor = app(GovernanceIdentityGateway::class)->current(str_repeat('a', 64));
    expect($actor->federated)->toBeTrue()->and($actor->installationAdministrator)->toBeFalse();
    Http::fake(['governance.example.test/identity/local-sessions' => Http::response(identityResponse())]);
    $session = app(GovernanceIdentityGateway::class)->login('admin', 'synthetic-password');
    expect($session->expiresAt)->toBe(identityResponse()['expires_at']);
    Http::assertSent(fn (OutboundRequest $request): bool => preg_match('/\A[a-f0-9]{32,64}\z/', $request->header('Idempotency-Key')[0] ?? '') === 1);
});

it('rejects an incompatible identity through the actual installed decoder', function (string $fault): void {
    $identity = ['subject' => '550e8400-e29b-41d4-a716-446655440000', 'kind' => 'federated',
        'password_change_required' => false, 'permissions' => ['identity.logout']];
    $invalid = match ($fault) {
        'unknown-field' => $identity + ['role' => 'admin'],
        'subject' => array_replace($identity, ['subject' => 'forged']),
        'permissions' => array_replace($identity, ['permissions' => ['identity.setup']]),
    };
    Http::fake(['governance.example.test/identity/session' => Http::response(['identity' => $invalid])]);
    expect(fn () => app(GovernanceIdentityGateway::class)->current(str_repeat('a', 64)))->toThrow(IdentityFailure::class);
})->with(['unknown-field', 'subject', 'permissions']);

it('renders an accessible sign-in page without making an identity call or exposing credentials', function (): void {
    Http::fake();
    $this->get('/login')->assertOk()->assertHeader('Cache-Control', 'no-store, private')
        ->assertInertia(fn (Assert $page): Assert => $page->component('identity/Login')->missing('session_token')->missing('credentials')->missing('password'));
    Http::assertNothingSent();
});

it('replaces the anonymous session and CSRF state and keeps the owner token server side', function (): void {
    Http::fake(['governance.example.test/identity/local-sessions' => Http::response(identityResponse())]);
    $this->withSession(['_token' => 'old-csrf', 'untrusted' => 'old-session-value']);
    $oldId = session()->getId();
    $response = $this->post('/login', ['username' => 'admin', 'password' => 'synthetic-temporary-password']);
    $response->assertRedirect('/password')->assertSessionHas('identity.token', str_repeat('a', 64))->assertSessionMissing('untrusted');
    expect(session()->getId())->not->toBe($oldId)
        ->and(session()->token())->not->toBe('old-csrf')
        ->and($response->getContent())->not->toContain(str_repeat('a', 64));
    Http::assertSent(fn (OutboundRequest $request): bool => $request->hasHeader('Authorization', 'Bearer '.$this->workloadCredential)
        && $request['password'] === 'synthetic-temporary-password');
});

it('rechecks owner authority on each protected page and blocks setup before password change', function (): void {
    Http::fake(['governance.example.test/identity/session' => Http::response(['identity' => identityResponse()['identity']])]);
    $this->withSession(['identity.token' => str_repeat('a', 64)])->get('/setup')->assertRedirect('/password');
    $this->get('/password')->assertOk()->assertInertia(fn (Assert $page): Assert => $page->component('identity/Password')->missing('session_token')->missing('password'));
    Http::assertSentCount(2);
    Http::assertSent(fn (OutboundRequest $request): bool => $request->hasHeader('X-Console-Session', str_repeat('a', 64)));
});

it('rotates session and CSRF again after changing the password and discards form values', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response(['identity' => identityResponse()['identity']]),
        'governance.example.test/identity/password' => Http::response(identityResponse(false, str_repeat('b', 64))),
    ]);
    $this->withSession(['identity.token' => str_repeat('a', 64), '_token' => 'before-change']);
    $oldId = session()->getId();
    $this->post('/password', ['current_password' => 'synthetic-temporary-password', 'password' => 'synthetic-new-password', 'password_confirmation' => 'synthetic-new-password'])
        ->assertRedirect('/setup')->assertSessionHas('identity.token', str_repeat('b', 64))->assertSessionMissing('_old_input.password');
    expect(session()->getId())->not->toBe($oldId)->and(session()->token())->not->toBe('before-change');
});

it('does not flash passwords after a rejected change and never exposes upstream diagnostics', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response(['identity' => identityResponse()['identity']]),
        'governance.example.test/identity/password' => Http::response(['code' => 'password_policy', 'message' => 'Request denied',
            'correlation_id' => '550e8400-e29b-41d4-a716-446655440000', 'retryable' => false], 422),
    ]);
    $this->withSession(['identity.token' => str_repeat('a', 64)])->from('/password')
        ->post('/password', ['current_password' => 'synthetic-temporary-password', 'password' => 'synthetic-temporary-password', 'password_confirmation' => 'synthetic-temporary-password'])
        ->assertRedirect('/password')->assertSessionHasErrors('password')
        ->assertSessionMissing('_old_input.current_password')->assertSessionMissing('_old_input.password')->assertSessionMissing('_old_input.password_confirmation');
    expect(json_encode(session()->all()))->not->toContain('private-provider-response')->not->toContain('synthetic-temporary-password');
});

it('invalidates revoked sessions and never trusts a forged browser identity', function (): void {
    Http::fake(['governance.example.test/identity/session' => Http::response(['code' => 'invalid_session', 'message' => 'Session denied',
        'correlation_id' => '550e8400-e29b-41d4-a716-446655440000', 'retryable' => false], 401)]);
    $this->withSession(['identity.token' => str_repeat('a', 64), 'identity.password_change_required' => false, 'identity.role' => 'admin'])
        ->get('/setup')->assertRedirect('/login')->assertSessionMissing('identity');
});

it('holds the session when the owner returns an incompatible error or expired credential', function (): void {
    Http::fake(['governance.example.test/identity/session' => Http::response(['error' => 'invalid_session', 'debug' => 'private diagnostics'], 401)]);
    $this->withSession(['identity.token' => str_repeat('a', 64)])->get('/setup')->assertStatus(503)
        ->assertSessionHas('identity.token')->assertDontSee('private diagnostics');
    $expired = identityResponse();
    $expired['expires_at'] = now()->subSecond()->toIso8601String();
    Http::fake(['governance.example.test/identity/local-sessions' => Http::response($expired)]);
    expect(fn () => app(GovernanceIdentityGateway::class)->login('admin', 'synthetic-password'))->toThrow(IdentityFailure::class);
});

it('fails closed on an unavailable owner while retaining the session for a retry', function (): void {
    Http::fake(['governance.example.test/*' => Http::response(['debug' => 'private diagnostics'], 503)]);
    $this->withSession(['identity.token' => str_repeat('a', 64)])->get('/setup')->assertStatus(503)
        ->assertDontSee('private diagnostics')->assertSessionHas('identity.token');
});

it('revokes owner authority before clearing the browser session on logout', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response(['identity' => identityResponse()['identity']]),
        'governance.example.test/identity/logout' => Http::response(['status' => 'signed_out']),
    ]);
    $this->withSession(['identity.token' => str_repeat('a', 64)])->post('/logout')->assertRedirect('/login')->assertSessionMissing('identity.token');
    Http::assertSent(fn (OutboundRequest $request): bool => str_ends_with($request->url(), '/identity/logout') && $request->hasHeader('X-Console-Session', str_repeat('a', 64)));
});

it('enforces real CSRF middleware before any login password or logout call', function (string $route): void {
    $this->app['env'] = 'csrf-check';
    Http::fake();
    $this->withSession(['identity.token' => str_repeat('a', 64), '_token' => 'known-token'])->post($route, ['username' => 'admin', 'password' => 'synthetic-password'])
        ->assertStatus(419);
    Http::assertNothingSent();
})->with(['/login', '/password', '/logout']);

it('accepts the matching CSRF token on the real login route', function (): void {
    $this->app['env'] = 'csrf-check';
    Http::fake(['governance.example.test/identity/local-sessions' => Http::response(identityResponse())]);
    $this->withSession(['_token' => 'known-token'])->post('/login', ['_token' => 'known-token', 'username' => 'admin', 'password' => 'synthetic-password'])->assertRedirect('/password');
});

it('rejects hostile hosts and ignores untrusted proxy host headers', function (): void {
    Http::fake();
    $this->get('https://attacker.example.test/login')->assertStatus(400);
    $this->withHeader('X-Forwarded-Host', 'attacker.example.test')->get(rtrim(config('app.url'), '/').'/login')->assertOk();
    Http::assertNothingSent();
});

it('refuses insecure nonloopback service addresses and absent workload credentials', function (): void {
    Http::fake();
    config(['identity.governance_url' => 'http://governance.example.test']);
    $this->post('/login', ['username' => 'admin', 'password' => 'synthetic-password'])->assertStatus(503);
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => null]);
    $this->post('/login', ['username' => 'admin', 'password' => 'synthetic-password'])->assertStatus(503);
    Http::assertNothingSent();
});
