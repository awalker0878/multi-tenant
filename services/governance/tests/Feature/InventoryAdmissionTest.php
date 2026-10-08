<?php

declare(strict_types=1);

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->tenant = tenantCommand($this, '/v1/tenants', ['name' => 'Discovery tenant', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $this->owner = DB::table('app.tenant_memberships')->where('tenant_id', $this->tenant)->value('actor_id');
    $this->inventoryFile = tempnam(sys_get_temp_dir(), 'p04-inventory-');
    $this->inventoryToken = bin2hex(random_bytes(32));
    file_put_contents($this->inventoryFile, $this->inventoryToken);
    config(['identity.service_credentials.inventory' => $this->inventoryFile]);
    $this->site = (string) Str::uuid();
    $this->input = ['owner_id' => $this->owner, 'site_id' => $this->site, 'policy_digest' => hash('sha256', 'synthetic-scope')];
    $this->path = '/v1/tenants/'.$this->tenant.'/inventory-collection-checks';
});

afterEach(function (): void {
    unlink($this->credentialFile);
    unlink($this->inventoryFile);
});

it('requires the Inventory workload and the currently active scoped owner', function (): void {
    $this->withHeader('Authorization', 'Bearer '.$this->workload)->postJson($this->path, $this->input)->assertUnauthorized();
    $this->withHeader('Authorization', 'Bearer '.$this->inventoryToken)->postJson($this->path, $this->input)
        ->assertOk()->assertJsonPath('native_write_authorized', false)->assertJsonPath('policy_digest', $this->input['policy_digest']);
    DB::table('app.tenants')->where('id', $this->tenant)->update(['state' => 'suspended']);
    $this->postJson($this->path, $this->input)->assertNotFound();
});

it('denies foreign sites revoked owners forged fields and recovery holds', function (): void {
    DB::table('app.tenant_memberships')->where('tenant_id', $this->tenant)->update(['site_id' => $this->site]);
    $this->withHeader('Authorization', 'Bearer '.$this->inventoryToken)->postJson($this->path, array_replace($this->input, ['site_id' => (string) Str::uuid()]))->assertForbidden();
    $this->postJson($this->path, $this->input + ['native_write_authorized' => true])->assertUnprocessable();
    DB::table('app.tenant_memberships')->where('tenant_id', $this->tenant)->update(['state' => 'revoked']);
    $this->postJson($this->path, $this->input)->assertNotFound();
    DB::table('app.tenant_memberships')->where('tenant_id', $this->tenant)->update(['state' => 'active']);
    $this->admission['state'] = 'held';
    file_put_contents($this->admissionFile, json_encode($this->admission));
    $this->postJson($this->path, $this->input)->assertStatus(503);
});

it('delegates Inventory actions with current role and exact site scope', function (): void {
    $grant = $this->withHeader('Authorization', 'Bearer '.$this->workload)->withHeader('X-Console-Session', $this->token)
        ->postJson('/v1/tenants/'.$this->tenant.'/actor-delegations', ['audience' => 'inventory', 'action' => 'inventory.admin', 'scope' => ['site_id' => $this->site, 'environment' => null, 'resource_id' => null]])->assertCreated()->json();
    $this->withHeader('Authorization', 'Bearer '.$this->inventoryToken)->withHeader('X-Actor-Delegation', $grant['delegation_token'])
        ->postJson('/v1/tenants/'.$this->tenant.'/delegated-authorizations', ['action' => 'inventory.admin', 'scope' => ['site_id' => $this->site, 'environment' => null, 'resource_id' => null]])
        ->assertOk()->assertJsonPath('audience', 'inventory');
    $this->postJson('/v1/tenants/'.$this->tenant.'/delegated-authorizations', ['action' => 'inventory.admin', 'scope' => ['site_id' => null, 'environment' => null, 'resource_id' => null]])->assertUnauthorized();
});

it('does not give ordinary readers discovery or enrollment authority', function (): void {
    tenantMember($this, $this->tenant, 'p04-reader', 'reader');
    $reader = federatedLogin($this, 'p04-reader');
    foreach (['inventory.admin', 'inventory.discover', 'inventory.match'] as $action) {
        $this->withHeader('Authorization', 'Bearer '.$this->workload)->withHeader('X-Console-Session', $reader)
            ->postJson('/v1/tenants/'.$this->tenant.'/actor-delegations', ['audience' => 'inventory', 'action' => $action, 'scope' => ['site_id' => $this->site, 'environment' => null, 'resource_id' => null]])->assertForbidden();
    }
});
