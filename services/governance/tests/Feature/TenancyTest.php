<?php

declare(strict_types=1);

use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->tenantA = tenantCommand($this, '/v1/tenants', ['name' => 'Tenant A', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $this->tenantB = tenantCommand($this, '/v1/tenants', ['name' => 'Tenant B', 'administrator_subject' => 'independent-b-owner'])->assertCreated()->json('id');
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

it('requires workload and federated identity and grants no implied estate-wide tenant access', function (): void {
    $this->withHeader('Authorization', 'Bearer invalid')->getJson('/v1/tenants')->assertUnauthorized();
    $this->withHeader('Authorization', 'Bearer '.$this->workload)->withHeader('X-Console-Session', $this->token)->getJson('/v1/tenants')
        ->assertOk()->assertJsonCount(1, 'tenants')->assertJsonPath('tenants.0.id', $this->tenantA);
    foreach ([$this->tenantB, '00000000-0000-4000-8000-000000000001'] as $tenant) {
        foreach (['', '/memberships', '/grants', '/quota', '/audit'] as $suffix) {
            $this->getJson('/v1/tenants/'.$tenant.$suffix)->assertNotFound();
        }
    }
    $ownerB = federatedLogin($this, 'independent-b-owner');
    $this->withHeader('X-Console-Session', $ownerB)->getJson('/v1/tenants')->assertOk()->assertJsonCount(1, 'tenants')->assertJsonPath('tenants.0.id', $this->tenantB);
    $this->getJson('/v1/tenants/'.$this->tenantA)->assertNotFound();
});

it('scopes role decisions by tenant site environment and current membership', function (): void {
    $member = tenantMember($this, $this->tenantA, 'author-a', 'author', ['site_id' => 'site-a', 'environment' => 'development']);
    $author = federatedLogin($this, 'author-a');
    $path = '/v1/tenants/'.$this->tenantA.'/authorization-decisions';
    $input = ['action' => 'application.write', 'scope' => ['site_id' => 'site-a', 'environment' => 'development', 'resource_id' => 'app-a']];
    $this->withHeader('X-Console-Session', $author)->postJson($path, $input)->assertOk()->assertJsonPath('authority_use', 'observation_only');
    $this->postJson($path, array_replace($input, ['scope' => ['site_id' => 'site-b', 'environment' => 'development']]))->assertForbidden();
    $this->postJson($path, array_replace($input, ['scope' => []]))->assertForbidden();
    $this->postJson($path, array_replace($input, ['action' => 'tenant.manage']))->assertForbidden();
    $this->postJson('/v1/tenants/'.$this->tenantB.'/authorization-decisions', $input)->assertNotFound();
    tenantMember($this, $this->tenantA, 'author-a', 'author', ['site_id' => 'site-a', 'environment' => 'development'], $member['revision'], 'revoked');
    $this->withHeader('X-Console-Session', $author)->postJson($path, $input)->assertNotFound();
    $this->getJson('/v1/tenants')->assertOk()->assertJsonCount(0, 'tenants');
});

it('bounds delegated grants and revokes them without trusting a stale browser role', function (): void {
    $member = tenantMember($this, $this->tenantA, 'reader-a', 'reader');
    $grant = tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/grants', ['membership_id' => $member['id'], 'action' => 'approval.decide',
        'site_id' => 'site-a', 'environment' => 'development', 'resource_id' => 'app-a', 'expires_at' => now()->addHour()->toIso8601String()])->assertOk()->json();
    $reader = federatedLogin($this, 'reader-a');
    $input = ['action' => 'approval.decide', 'scope' => ['site_id' => 'site-a', 'environment' => 'development', 'resource_id' => 'app-a'], 'role' => 'tenant_admin'];
    $path = '/v1/tenants/'.$this->tenantA.'/authorization-decisions';
    $this->withHeader('X-Console-Session', $reader)->postJson($path, $input)->assertOk();
    $input['scope']['resource_id'] = 'app-b';
    $this->postJson($path, $input)->assertForbidden();
    $input['scope']['resource_id'] = 'app-a';
    tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/grant-revocations', ['grant_id' => $grant['id'], 'revision' => 1, 'reason' => 'End of review assignment'])->assertOk();
    $this->withHeader('X-Console-Session', $reader)->postJson($path, $input)->assertForbidden();
});

it('invalidates old delegated grants when membership revision changes and denies unknown support actions', function (): void {
    $member = tenantMember($this, $this->tenantA, 'reader-a', 'reader');
    tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/grants', ['membership_id' => $member['id'], 'action' => 'approval.decide',
        'site_id' => null, 'environment' => null, 'resource_id' => null, 'expires_at' => now()->addHour()->toIso8601String()])->assertOk();
    tenantMember($this, $this->tenantA, 'reader-a', 'reader', [], 1);
    $reader = federatedLogin($this, 'reader-a');
    foreach (['approval.decide', 'support.impersonate', 'tenant.export_all', '*'] as $action) {
        $this->withHeader('X-Console-Session', $reader)->postJson('/v1/tenants/'.$this->tenantA.'/authorization-decisions', ['action' => $action, 'scope' => []])->assertForbidden();
    }
});

it('rejects guessed cross-tenant membership and grant identifiers', function (): void {
    $b = DB::table('app.tenant_memberships')->where('tenant_id', $this->tenantB)->first();
    tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/grants', ['membership_id' => $b->id, 'action' => 'application.write',
        'site_id' => null, 'environment' => null, 'resource_id' => null, 'expires_at' => now()->addHour()->toIso8601String()])->assertStatus(422);
    tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/grant-revocations', ['grant_id' => $b->id, 'revision' => 1, 'reason' => 'guessed'])->assertNotFound();
    expect(DB::table('app.delegated_grants')->count())->toBe(0);
});

it('keeps quota entitlement distinct from capacity and reservations with revision and retry guards', function (): void {
    $path = '/v1/tenants/'.$this->tenantA.'/quota';
    $input = ['revision' => 0, 'entitlement' => ['vcpu' => 40, 'memory_mib' => 131072, 'storage_gib' => 2048, 'workloads' => 30]];
    $first = tenantCommand($this, $path, $input, key: 'quota-command-01')->assertOk()->json();
    tenantCommand($this, $path, $input, key: 'quota-command-01')->assertOk()->assertExactJson($first);
    $input['entitlement']['vcpu'] = 400;
    tenantCommand($this, $path, $input, key: 'quota-command-01')->assertStatus(409);
    tenantCommand($this, $path, $input)->assertStatus(409);
    $this->getJson($path)->assertOk()->assertJsonPath('entitlement.vcpu', 40)->assertJsonPath('observed_capacity', null)->assertJsonPath('reservations', null);
    expect(DB::table('app.governance_audit')->where('event', 'governance.quota.changed')->count())->toBe(1)
        ->and(DB::table('app.governance_outbox')->where('event', 'governance.quota.changed')->count())->toBe(1);
});

it('preserves independent immutable histories and refuses removal of the last tenant administrator', function (): void {
    tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/memberships', ['revision' => 1, 'subject' => 'immutable-admin-subject', 'role' => 'reader',
        'state' => 'revoked', 'site_id' => null, 'environment' => null, 'expires_at' => null])->assertStatus(409);
    $this->getJson('/v1/tenants/'.$this->tenantA.'/audit')->assertOk()->assertJsonCount(1, 'audit')->assertJsonPath('audit.0.tenant_id', $this->tenantA);
    $this->getJson('/v1/tenants/'.$this->tenantB.'/audit')->assertNotFound();
});

it('suspends new access and permits the scoped tenant administrator to restore it', function (): void {
    tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/state', ['revision' => 1, 'state' => 'suspended'])->assertOk();
    $this->getJson('/v1/tenants/'.$this->tenantA)->assertNotFound();
    tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/state', ['revision' => 2, 'state' => 'active'])->assertOk();
    $this->getJson('/v1/tenants/'.$this->tenantA)->assertOk()->assertJsonPath('tenant.revision', 3);
});

it('rolls back quota and command receipts if its durable outbox fails', function (): void {
    $this->withoutExceptionHandling();
    DB::statement('DROP TABLE app.governance_outbox');
    expect(fn () => tenantCommand($this, '/v1/tenants/'.$this->tenantA.'/quota', ['revision' => 0,
        'entitlement' => ['vcpu' => 1, 'memory_mib' => 1, 'storage_gib' => 1, 'workloads' => 1]]))->toThrow(QueryException::class);
    expect(DB::table('app.tenant_quotas')->count())->toBe(0)
        ->and(DB::table('app.governance_commands')->where('command', 'quota')->count())->toBe(0);
});
