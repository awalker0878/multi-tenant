<?php

declare(strict_types=1);

use App\Application\Authorization\Data\ActorContext;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Route;

beforeEach(function (): void {
    Http::preventStrayRequests();
    $this->callerFile = tempnam(sys_get_temp_dir(), 'p02-caller-');
    $this->authorityFile = tempnam(sys_get_temp_dir(), 'p02-authority-');
    $this->caller = bin2hex(random_bytes(32));
    $this->authority = bin2hex(random_bytes(32));
    $this->delegation = bin2hex(random_bytes(32));
    file_put_contents($this->callerFile, $this->caller);
    file_put_contents($this->authorityFile, $this->authority);
    config(['authorization.console_credential_file' => $this->callerFile, 'authorization.governance_credential_file' => $this->authorityFile,
        'authorization.governance_url' => 'https://governance.example.test']);
    $this->tenant = '550e8400-e29b-41d4-a716-446655440001';
    $this->actor = '550e8400-e29b-41d4-a716-446655440002';
    $this->scope = ['site_id' => 'site-a', 'environment' => 'development', 'resource_id' => 'app-a'];
    $this->decision = ['allowed' => true, 'delegation_id' => '550e8400-e29b-41d4-a716-446655440003', 'actor_id' => $this->actor,
        'tenant_id' => $this->tenant, 'audience' => 'catalogue', 'delegating_service' => 'console',
        'action' => 'application.read', 'scope' => $this->scope, 'expires_at' => now()->addMinute()->toIso8601String(),
        'evaluated_at' => now()->toIso8601String(), 'authority_use' => 'request_bound'];
    $this->path = '/p02-fixture/'.$this->tenant.'/site-a/development/app-a';
    $ownedTenant = $this->tenant;
    // Test-only owner resource. Real P03 resources must apply the same tenant and
    // site/environment predicates, in addition to this middleware's decision.
    Route::get('/p02-fixture/{tenant}/{site}/{environment}/{application}', function (Request $request) use ($ownedTenant) {
        $actor = $request->attributes->get('verified_actor');
        abort_unless($actor instanceof ActorContext && $actor->tenantId === $ownedTenant
            && $actor->scope === ['site_id' => 'site-a', 'environment' => 'development', 'resource_id' => 'app-a'], 404);

        return response()->json(['actor' => $actor->actorId, 'tenant' => $actor->tenantId, 'fixture' => true]);
    })->middleware('delegated:application.read');
    $this->withToken($this->caller)->withHeader('X-Actor-Delegation', $this->delegation);
});

afterEach(function (): void {
    unlink($this->callerFile);
    unlink($this->authorityFile);
});

it('uses its independent service credential and route scope and ignores forged actor fields', function (): void {
    Http::fake(['governance.example.test/*' => Http::response($this->decision)]);
    $this->getJson($this->path.'?actor_id=administrator&tenant_id=foreign&resource_id=app-b')->assertOk()
        ->assertJsonPath('actor', $this->actor)->assertHeader('Cache-Control', 'no-store, private');
    Http::assertSent(fn ($request): bool => $request->hasHeader('Authorization', 'Bearer '.$this->authority)
        && $request->hasHeader('X-Actor-Delegation', $this->delegation) && ! $request->hasHeader('X-Console-Session')
        && $request['scope'] === $this->scope && $request['action'] === 'application.read');
});

it('requires independent caller identity and actor delegation before protected resource access', function (): void {
    $this->withToken($this->authority)->getJson($this->path)->assertUnauthorized();
    $this->withToken($this->caller)->withHeader('X-Actor-Delegation', '')->getJson($this->path)->assertForbidden();
    Http::assertNothingSent();
});

it('never caches authority between allowed revoked and recovered requests', function (): void {
    Http::fake(['governance.example.test/*' => Http::sequence()->push($this->decision)->push(['error' => 'invalid_delegation'], 401)->push($this->decision)]);
    $this->getJson($this->path)->assertOk();
    $this->getJson($this->path)->assertForbidden();
    $this->getJson($this->path)->assertOk();
    Http::assertSentCount(3);
});

it('holds malformed stale widened and wrong-audience authority responses', function (string $field, mixed $value): void {
    Http::fake(['governance.example.test/*' => Http::response(array_replace($this->decision, [$field => $value]))]);
    $this->getJson($this->path)->assertStatus(503)->assertExactJson(['error' => 'access_unavailable']);
})->with([
    ['audience', 'planning'], ['actor_id', 'forged'], ['allowed', 'true'], ['authority_use', 'observation_only'],
    ['tenant_id', '550e8400-e29b-41d4-a716-446655440099'], ['scope', ['site_id' => null, 'environment' => null, 'resource_id' => null]],
    ['expires_at', '2000-01-01T00:00:00Z'], ['evaluated_at', '2000-01-01T00:00:00Z'],
]);

it('fails closed on redirects and missing workload custody', function (): void {
    Http::fake(['governance.example.test/*' => Http::response('', 302, ['Location' => 'https://untrusted.example.test'])]);
    $this->getJson($this->path)->assertStatus(503);
    file_put_contents($this->authorityFile, '');
    $this->getJson($this->path)->assertStatus(503);
    Http::assertSentCount(1);
});

it('retains the owning resource tenant check even if a remote response is valid for another tenant', function (): void {
    $other = '550e8400-e29b-41d4-a716-446655440099';
    Http::fake(['governance.example.test/*' => Http::response(array_replace($this->decision, ['tenant_id' => $other]))]);
    $this->getJson(str_replace($this->tenant, $other, $this->path))->assertNotFound();
});
