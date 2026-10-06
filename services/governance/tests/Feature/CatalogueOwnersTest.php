<?php

declare(strict_types=1);

use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->tenant = tenantCommand($this, '/v1/tenants', ['name' => 'Catalogue tenant', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $this->member = tenantMember($this, $this->tenant, 'catalogue-author', 'author');
    $this->author = federatedLogin($this, 'catalogue-author');
    $this->serviceFile = tempnam(sys_get_temp_dir(), 'p03-catalogue-');
    $this->serviceToken = bin2hex(random_bytes(32));
    file_put_contents($this->serviceFile, $this->serviceToken);
    config(['identity.service_credentials.catalogue' => $this->serviceFile]);
    $this->scope = ['site_id' => null, 'environment' => null, 'resource_id' => null];
});

afterEach(function (): void {
    unlink($this->credentialFile);
    unlink($this->serviceFile);
});

it('gives reference administration only to the current tenant administrator', function (): void {
    $input = ['audience' => 'catalogue', 'action' => 'reference.write', 'scope' => $this->scope];
    $this->withHeader('X-Console-Session', $this->author)->postJson('/v1/tenants/'.$this->tenant.'/actor-delegations', $input)->assertForbidden();
    $this->withHeader('X-Console-Session', $this->token)->postJson('/v1/tenants/'.$this->tenant.'/actor-delegations', $input)->assertCreated();
    $this->withHeader('X-Console-Session', $this->author)->postJson('/v1/tenants/'.$this->tenant.'/actor-delegations', array_replace($input, ['action' => 'reference.read']))->assertCreated();
});

it('validates service owners against current tenant membership and denies guessed or disabled principals', function (): void {
    $grant = $this->withHeader('X-Console-Session', $this->author)->postJson('/v1/tenants/'.$this->tenant.'/actor-delegations', ['audience' => 'catalogue', 'action' => 'application.write', 'scope' => $this->scope])->assertCreated()->json();
    $this->withHeader('Authorization', 'Bearer '.$this->serviceToken)->withHeader('X-Actor-Delegation', $grant['delegation_token']);
    $path = '/v1/tenants/'.$this->tenant.'/catalogue-owner-checks';
    $input = ['action' => 'application.write', 'scope' => $this->scope, 'owners' => [$this->member['actor_id']]];
    $this->postJson($path, $input)->assertOk()->assertJsonPath('owners.0', $this->member['actor_id']);
    $this->postJson($path, array_replace($input, ['owners' => ['00000000-0000-4000-8000-000000000999']]))->assertStatus(422);
    DB::table('app.federated_actors')->where('id', $this->member['actor_id'])->update(['disabled_at' => now()]);
    $this->postJson($path, $input)->assertUnauthorized();
});
