<?php

declare(strict_types=1);

use App\Application\Identity\Actions\BootstrapAdministrator;
use App\Application\Identity\Contracts\OidcHttpTransport;
use App\Domain\Identity\BootstrapAdministrator as Administrator;
use App\Infrastructure\Identity\OidcHttpClient;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Tests\Support\SyntheticOidcTransport;

beforeEach(function (): void {
    initializeIdentityFixture($this);
    $this->provider = new SyntheticOidcTransport;
    app()->instance(OidcHttpTransport::class, $this->provider);
    $this->token = changeLocalPassword($this, localLogin($this));
    $this->withHeader('X-Console-Session', $this->token);
    $this->settings = ['revision' => 0, 'issuer' => 'https://idp.example.test/realm', 'client_id' => 'console-client',
        'client_secret' => 'synthetic-oidc-secret', 'redirect_uri' => 'https://console.example.test/identity/callback',
        'administrator_subject' => 'immutable-admin-subject', 'private_networks' => []];
    $this->binding = bin2hex(random_bytes(32));
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

it('stores secret references with encrypted custody and rejects pre-change access and stale writes', function (): void {
    saveConnection($this);
    $projection = $this->getJson('/identity/oidc')->assertOk()->assertJsonPath('revision', 1)->assertJsonPath('active_revision', null)->getContent();
    expect($projection)->not->toContain('synthetic-oidc-secret')->not->toContain('secret_ref')->not->toContain('ciphertext');
    $secret = DB::table('app.identity_secrets')->first();
    expect($secret->ciphertext)->not->toContain('synthetic-oidc-secret')->and(Crypt::decryptString($secret->ciphertext))->toBe('synthetic-oidc-secret');
    $this->putJson('/identity/oidc', $this->settings)->assertStatus(409);
    expect(DB::table('app.oidc_connections')->count())->toBe(1)->and(DB::table('app.identity_secrets')->count())->toBe(1);
    Administrator::query()->whereKey(1)->update(['state' => 'password_change_required']);
    $this->getJson('/identity/oidc')->assertForbidden();
    $this->postJson('/identity/oidc/flows', ['purpose' => 'setup', 'browser_binding' => $this->binding])->assertForbidden();
    $this->putJson('/identity/oidc', $this->settings)->assertForbidden();
});

it('preserves local setup after provider failure and never activates on settings alone', function (): void {
    saveConnection($this);
    $this->postJson('/identity/oidc/activation', ['verification_token' => str_repeat('a', 64)])->assertStatus(409);
    $this->provider->unavailable = true;
    $this->postJson('/identity/oidc/flows', ['purpose' => 'setup', 'browser_binding' => $this->binding])->assertStatus(503);
    $this->getJson('/identity/setup')->assertOk();
    expect(Administrator::query()->findOrFail(1)->state)->toBe('local_setup');
});

it('uses real signed tokens, verifies PKCE and atomically retires every local session', function (): void {
    $other = localLogin($this, 'a different long password');
    $federated = activateFederation($this);
    foreach ([$this->token, $other] as $local) {
        $this->withHeader('X-Console-Session', $local)->getJson('/identity/session')->assertUnauthorized();
    }
    $this->withHeader('X-Console-Session', $federated)->getJson('/identity/session')->assertOk()->assertJsonPath('identity.kind', 'federated');
    $this->getJson('/identity/oidc')->assertOk()->assertJsonPath('active_revision', 1);
    expect(Administrator::query()->findOrFail(1)->state)->toBe('retired')->and(app(BootstrapAdministrator::class)->handle())->toBeNull()
        ->and(DB::table('app.identity_sessions')->whereNull('revoked_at')->count())->toBe(0);
    $this->provider->unavailable = true;
    $this->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => 'a different long password'])->assertUnauthorized();
    $this->postJson('/identity/oidc/flows', ['purpose' => 'login', 'browser_binding' => $this->binding])->assertStatus(503);
    $stored = json_encode([DB::table('app.oidc_flows')->get(), DB::table('app.identity_audit')->get(), DB::table('app.federated_sessions')->get()]);
    expect($stored)->not->toContain('must-not-be-persisted')->not->toContain($federated);
});

it('denies forged issuer audience expiry nonce authorized party and administrator subject', function (array $claims): void {
    saveConnection($this);
    $this->provider->claims = $claims;
    $this->postJson('/identity/oidc/callback', beginFederation($this))->assertStatus(isset($claims['sub']) ? 403 : 401);
    expect(DB::table('app.oidc_verifications')->count())->toBe(0)->and(Administrator::query()->findOrFail(1)->state)->toBe('local_setup');
})->with([
    'issuer' => [['iss' => 'https://forged.example.test']], 'audience' => [['aud' => 'another-client']],
    'expired' => [['exp' => 1]], 'missing expiry' => [['exp' => null]], 'nonce' => [['nonce' => 'wrong']],
    'party' => [['aud' => ['console-client', 'other'], 'azp' => 'other']], 'missing party' => [['aud' => ['console-client', 'other']]],
    'ungranted subject' => [['sub' => 'another-admin']], 'old authentication' => [['auth_time' => 1]], 'invalid timestamp' => [['iat' => '123']],
]);

it('rejects a forged signature and consumes the failed flow', function (): void {
    saveConnection($this);
    $this->provider->badSignature = true;
    $callback = beginFederation($this);
    $this->postJson('/identity/oidc/callback', $callback)->assertUnauthorized();
    $this->provider->badSignature = false;
    $this->postJson('/identity/oidc/callback', $callback)->assertUnauthorized()->assertJsonPath('error', 'invalid_oidc_flow');
});

it('binds browser state and proof to their initiating session and settings revision', function (): void {
    saveConnection($this);
    $callback = beginFederation($this);
    $this->postJson('/identity/oidc/callback', array_replace($callback, ['browser_binding' => str_repeat('f', 64)]))->assertUnauthorized();
    $proof = $this->postJson('/identity/oidc/callback', $callback)->assertOk()->json('verification_token');
    $this->postJson('/identity/oidc/callback', $callback)->assertUnauthorized();
    $other = localLogin($this, 'a different long password');
    $this->withHeader('X-Console-Session', $other)->postJson('/identity/oidc/activation', ['verification_token' => $proof])->assertStatus(409);
    saveConnection($this, ['revision' => 1, 'client_secret' => '']);
    $this->postJson('/identity/oidc/activation', ['verification_token' => $proof])->assertStatus(409);
    expect(DB::table('app.identity_secrets')->count())->toBe(1);
});

it('expires sign-in attempts and handover proofs', function (): void {
    saveConnection($this);
    $callback = beginFederation($this);
    $this->travel(6)->minutes();
    $this->postJson('/identity/oidc/callback', $callback)->assertUnauthorized();
    $this->travelBack();
    $proof = $this->postJson('/identity/oidc/callback', beginFederation($this))->assertOk()->json('verification_token');
    $this->travel(6)->minutes();
    $this->postJson('/identity/oidc/activation', ['verification_token' => $proof])->assertStatus(409);
});

it('keeps the active connection during draft edits and denies setup to an ordinary federated identity', function (): void {
    $this->token = activateFederation($this);
    saveConnection($this, ['revision' => 1]);
    $this->getJson('/identity/oidc')->assertOk()->assertJsonPath('active_revision', 1)->assertJsonPath('revision', 2);
    $this->provider->claims = ['sub' => 'ordinary-subject'];
    $user = $this->postJson('/identity/oidc/callback', beginFederation($this, 'login', ''))->assertOk()->json('session_token');
    $this->withHeader('X-Console-Session', $user)->getJson('/identity/session')->assertOk()->assertJsonPath('identity.permissions', ['identity.logout']);
    $this->getJson('/identity/oidc')->assertForbidden();
    $this->postJson('/identity/logout')->assertOk();
    $this->getJson('/identity/session')->assertUnauthorized();
});

it('rolls activation back if its audit outbox cannot commit', function (): void {
    saveConnection($this);
    $proof = $this->postJson('/identity/oidc/callback', beginFederation($this))->assertOk()->json('verification_token');
    $this->withoutExceptionHandling();
    DB::statement('DROP TABLE app.identity_outbox');
    expect(fn () => $this->postJson('/identity/oidc/activation', ['verification_token' => $proof]))->toThrow(QueryException::class);
    $this->withExceptionHandling();
    expect(Administrator::query()->findOrFail(1)->state)->toBe('local_setup')
        ->and(DB::table('app.oidc_installation')->value('active_revision'))->toBeNull()
        ->and(DB::table('app.oidc_verifications')->value('consumed_at'))->toBeNull();
    $this->getJson('/identity/setup')->assertOk();
});

it('refuses insecure URLs and discovery that redirects authority or secrets', function (): void {
    $this->putJson('/identity/oidc', array_replace($this->settings, ['issuer' => 'http://idp.example.test']))->assertStatus(422);
    saveConnection($this);
    $this->provider->metadata = ['token_endpoint' => 'https://attacker.example.test/token'];
    $this->postJson('/identity/oidc/flows', ['purpose' => 'setup', 'browser_binding' => $this->binding])->assertStatus(422);
    expect(DB::table('app.oidc_flows')->count())->toBe(0);
});

it('denies metadata and loopback targets and permits only selected private networks', function (): void {
    $http = new OidcHttpClient;
    foreach (['127.0.0.1', '169.254.169.254', '::1', '::ffff:127.0.0.1', '100.100.100.200', '224.0.0.1', '0.0.0.0', 'fe80::1'] as $ip) {
        expect($http->permits($ip, ['10.0.0.0/8']))->toBeFalse();
    }
    expect($http->permits('10.40.80.10', []))->toBeFalse()->and($http->permits('10.40.80.10', ['10.40.80.0/22']))->toBeTrue()
        ->and($http->permits('10.41.1.1', ['10.40.80.0/22']))->toBeFalse()->and($http->permits('8.8.8.8', []))->toBeTrue();
});
