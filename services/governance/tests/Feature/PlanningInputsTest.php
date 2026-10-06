<?php

declare(strict_types=1);

use App\Domain\Approvals\BoundPlan;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->tenant = tenantCommand($this, '/v1/tenants', ['name' => 'Planning tenant', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $this->member = tenantMember($this, $this->tenant, 'planning-author', 'author');
    $this->author = federatedLogin($this, 'planning-author');
    $this->files = [];
    $this->tokens = [];
    foreach (['planning', 'catalogue', 'inventory', 'assurance'] as $service) {
        $this->files[$service] = tempnam(sys_get_temp_dir(), 'p05-owner-');
        $this->tokens[$service] = bin2hex(random_bytes(32));
        file_put_contents($this->files[$service], $this->tokens[$service]);
        config(['identity.service_credentials.'.$service => $this->files[$service]]);
    }
    $this->scope = ['site_id' => (string) Str::uuid(), 'environment' => (string) Str::uuid(), 'resource_id' => (string) Str::uuid()];
    $grant = $this->withHeader('Authorization', 'Bearer '.$this->workload)->withHeader('X-Console-Session', $this->author)
        ->postJson('/v1/tenants/'.$this->tenant.'/actor-delegations', ['audience' => 'planning', 'action' => 'plan.create', 'scope' => $this->scope])->assertCreated()->json();
    $this->delegation = $grant['delegation_token'];
    $this->input = ['action' => 'plan.create', 'scope' => $this->scope];
    $this->path = '/v1/tenants/'.$this->tenant.'/planning-input-checks';
});

afterEach(function (): void {
    unlink($this->credentialFile);
    foreach ($this->files as $file) {
        unlink($file);
    }
});

it('checks the original planning actor separately at each source owner', function (): void {
    foreach (['catalogue', 'inventory', 'assurance'] as $owner) {
        $this->withHeader('Authorization', 'Bearer '.$this->tokens[$owner])->withHeader('X-Actor-Delegation', $this->delegation)
            ->postJson($this->path, $this->input)->assertOk()->assertJsonPath('source_owner', $owner)->assertJsonPath('source_use', 'planning_read_only')->assertJsonPath('actor_id', $this->member['actor_id']);
    }
    $this->withHeader('Authorization', 'Bearer '.$this->tokens['planning'])->postJson($this->path, $this->input)->assertForbidden();
});

it('denies widened scopes revocation and mismatched operation', function (): void {
    $this->withHeader('Authorization', 'Bearer '.$this->tokens['catalogue'])->withHeader('X-Actor-Delegation', $this->delegation);
    $this->postJson($this->path, ['action' => 'plan.read', 'scope' => $this->scope])->assertUnauthorized();
    $this->postJson($this->path, ['action' => 'plan.create', 'scope' => array_replace($this->scope, ['site_id' => (string) Str::uuid()])])->assertUnauthorized();
    DB::table('app.tenant_memberships')->where('tenant_id', $this->tenant)->where('actor_id', $this->member['actor_id'])->update(['state' => 'revoked']);
    $this->postJson($this->path, $this->input)->assertNotFound();
});

it('verifies Python canonical content binding and rejects an altered digest', function (): void {
    $path = dirname(__DIR__).'/Fixtures/synthetic-plan-v1.json';
    $fixture = json_decode(file_get_contents($path), true, 64, JSON_THROW_ON_ERROR);
    $bound = BoundPlan::fromArray($fixture['binding']);
    expect(GovernanceLedger::digest($fixture['content']))->toBe($bound->binding['content_digest']);
    $changed = $fixture['binding'];
    $changed['content_digest'] = str_repeat('a', 64);
    expect(fn () => BoundPlan::fromArray($changed))->toThrow(IdentityDenied::class);
});
