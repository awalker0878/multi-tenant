<?php

declare(strict_types=1);

use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Testing\TestResponse;

beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->tenant = tenantCommand($this, '/v1/tenants', ['name' => 'Delegation tenant', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $this->member = tenantMember($this, $this->tenant, 'delegated-author', 'author');
    $this->author = federatedLogin($this, 'delegated-author');
    $this->serviceFiles = [];
    $this->serviceTokens = [];
    foreach (['catalogue', 'planning', 'assurance'] as $service) {
        $this->serviceFiles[$service] = tempnam(sys_get_temp_dir(), 'p02-service-');
        $this->serviceTokens[$service] = bin2hex(random_bytes(32));
        file_put_contents($this->serviceFiles[$service], $this->serviceTokens[$service]);
        config(['identity.service_credentials.'.$service => $this->serviceFiles[$service]]);
    }
    $this->input = ['audience' => 'catalogue', 'action' => 'application.read', 'scope' => ['site_id' => 'site-a', 'environment' => 'development', 'resource_id' => 'app-a']];
    $this->issuePath = '/v1/tenants/'.$this->tenant.'/actor-delegations';
    $this->inspectPath = '/v1/tenants/'.$this->tenant.'/delegated-authorizations';
});

afterEach(function (): void {
    unlink($this->credentialFile);
    foreach ($this->serviceFiles as $path) {
        if (is_file($path)) {
            unlink($path);
        }
    }
    $this->travelBack();
});

function issueDelegation(object $test): array
{
    return $test->withHeader('Authorization', 'Bearer '.$test->workload)->withHeader('X-Console-Session', $test->author)
        ->postJson($test->issuePath, $test->input)->assertCreated()->json();
}

function inspectDelegation(object $test, array $grant, string $audience = 'catalogue', ?array $input = null): TestResponse
{
    return $test->withHeader('Authorization', 'Bearer '.$test->serviceTokens[$audience])->withHeader('X-Console-Session', '')
        ->withHeader('X-Actor-Delegation', $grant['delegation_token'])->postJson($test->inspectPath, $input ?? ['action' => $test->input['action'], 'scope' => $test->input['scope']]);
}

it('binds an opaque delegation to current actor service action and exact scope', function (): void {
    $grant = issueDelegation($this);
    inspectDelegation($this, $grant)->assertOk()->assertJsonPath('actor_id', $this->member['actor_id'])
        ->assertJsonPath('delegating_service', 'console')->assertJsonPath('audience', 'catalogue')
        ->assertJsonPath('tenant_id', $this->tenant)->assertJsonPath('scope.resource_id', 'app-a')
        ->assertHeader('Cache-Control', 'no-store, private');
    $row = DB::table('app.actor_delegations')->sole();
    expect($row->token_hash)->toBe(hash('sha256', $grant['delegation_token']))
        ->and(json_encode(DB::table('app.actor_delegations')->get()))->not->toContain($grant['delegation_token'])
        ->and(DB::table('app.delegation_audit')->value('event'))->toBe('issued');
});

it('rejects the wrong service and changed action or resource scope', function (): void {
    $grant = issueDelegation($this);
    inspectDelegation($this, $grant, 'planning')->assertUnauthorized();
    foreach ([['action' => 'application.write'], ['scope' => ['site_id' => 'site-b', 'environment' => 'development', 'resource_id' => 'app-a']],
        ['scope' => ['site_id' => null, 'environment' => null, 'resource_id' => null]]] as $changes) {
        inspectDelegation($this, $grant, 'catalogue', array_replace(['action' => $this->input['action'], 'scope' => $this->input['scope']], $changes))->assertUnauthorized();
    }
    $this->inspectPath = '/v1/tenants/550e8400-e29b-41d4-a716-446655440222/delegated-authorizations';
    inspectDelegation($this, $grant)->assertUnauthorized();
});

it('rejects service identity alone and never accepts console identity as the target service', function (): void {
    $grant = issueDelegation($this);
    $this->withHeader('Authorization', 'Bearer '.$this->serviceTokens['catalogue'])->withHeader('X-Actor-Delegation', '')
        ->postJson($this->inspectPath, ['action' => $this->input['action'], 'scope' => $this->input['scope']])->assertUnauthorized();
    $this->withHeader('Authorization', 'Bearer '.$this->workload)->withHeader('X-Actor-Delegation', $grant['delegation_token'])
        ->postJson($this->inspectPath, ['action' => $this->input['action'], 'scope' => $this->input['scope']])->assertUnauthorized();
});

it('expires within sixty seconds and cannot extend its source session lifetime', function (): void {
    DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $this->author))->update(['expires_at' => now()->addSeconds(20)]);
    $grant = issueDelegation($this);
    $this->travel(21)->seconds();
    inspectDelegation($this, $grant)->assertUnauthorized();
});

it('immediately denies logout disabled actors and credential rotation', function (string $change): void {
    $grant = issueDelegation($this);
    match ($change) {
        'logout' => DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $this->author))->update(['revoked_at' => now()]),
        'actor' => DB::table('app.federated_actors')->where('id', $this->member['actor_id'])->update(['disabled_at' => now()]),
        'console' => file_put_contents($this->credentialFile, bin2hex(random_bytes(32))),
        'service' => file_put_contents($this->serviceFiles['catalogue'], bin2hex(random_bytes(32))),
    };
    inspectDelegation($this, $grant)->assertUnauthorized();
})->with(['logout', 'actor', 'console', 'service']);

it('denies the old delegation with a newly rotated valid service credential', function (): void {
    $grant = issueDelegation($this);
    $this->serviceTokens['catalogue'] = bin2hex(random_bytes(32));
    file_put_contents($this->serviceFiles['catalogue'], $this->serviceTokens['catalogue']);
    inspectDelegation($this, $grant)->assertUnauthorized();
    inspectDelegation($this, issueDelegation($this))->assertOk();
});

it('cannot revive a delegated request after membership revocation and regrant', function (): void {
    $grant = issueDelegation($this);
    $this->withHeader('Authorization', 'Bearer '.$this->workload);
    tenantMember($this, $this->tenant, 'delegated-author', 'author', [], 1, 'revoked');
    inspectDelegation($this, $grant)->assertNotFound();
    $this->withHeader('Authorization', 'Bearer '.$this->workload);
    tenantMember($this, $this->tenant, 'delegated-author', 'author', [], 2, 'active');
    inspectDelegation($this, $grant)->assertUnauthorized();
});

it('permits only its originating actor to revoke and records one immutable receipt', function (): void {
    $grant = issueDelegation($this);
    $path = $this->issuePath.'/'.$grant['delegation_id'].'/revocation';
    $this->withHeader('Authorization', 'Bearer '.$this->workload)->withHeader('X-Console-Session', $this->token)->postJson($path)->assertNotFound();
    $this->withHeader('X-Console-Session', $this->author)->postJson($path)->assertOk();
    $this->postJson($path)->assertOk();
    inspectDelegation($this, $grant)->assertUnauthorized();
    expect(DB::table('app.delegation_audit')->where('event', 'revoked')->count())->toBe(1);
});

it('denies administrative native and support delegation and caller supplied actor fields', function (): void {
    $this->withHeader('Authorization', 'Bearer '.$this->workload)->withHeader('X-Console-Session', $this->author);
    foreach (['membership.manage', 'support.access', 'operation.admit', 'approval.decide'] as $action) {
        $this->postJson($this->issuePath, array_replace($this->input, ['action' => $action]))->assertForbidden();
    }
    $this->postJson($this->issuePath, $this->input + ['actor_id' => $this->member['actor_id']])->assertUnprocessable();
    $this->postJson($this->issuePath, array_replace($this->input, ['scope' => $this->input['scope'] + ['role' => 'admin']]))->assertUnprocessable();
    expect(DB::table('app.actor_delegations')->count())->toBe(0);
});

it('fails closed on missing or shared service credentials and rolls back issuance audit failure', function (): void {
    file_put_contents($this->serviceFiles['planning'], $this->serviceTokens['catalogue']);
    $this->withHeader('Authorization', 'Bearer '.$this->workload)->withHeader('X-Console-Session', $this->author)
        ->postJson($this->issuePath, $this->input)->assertUnauthorized();
    file_put_contents($this->serviceFiles['planning'], $this->serviceTokens['planning']);
    unlink($this->serviceFiles['catalogue']);
    $this->postJson($this->issuePath, $this->input)->assertStatus(503);
    file_put_contents($this->serviceFiles['catalogue'], $this->serviceTokens['catalogue']);
    DB::statement('DROP TABLE app.delegation_audit');
    $this->withoutExceptionHandling();
    expect(fn () => $this->postJson($this->issuePath, $this->input))->toThrow(QueryException::class);
    expect(DB::table('app.actor_delegations')->count())->toBe(0);
});
