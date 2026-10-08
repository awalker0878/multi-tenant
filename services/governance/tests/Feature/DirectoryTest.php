<?php

declare(strict_types=1);

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->tenant = tenantCommand($this, '/v1/tenants', ['name' => 'Directory tenant', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $this->other = tenantCommand($this, '/v1/tenants', ['name' => 'Other tenant', 'administrator_subject' => 'other-owner'])->assertCreated()->json('id');
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

function directoryMembers(string $tenant, int $count): void
{
    $member = (array) DB::table('app.tenant_memberships')->where('tenant_id', $tenant)->first();
    $actor = (array) DB::table('app.federated_actors')->where('id', $member['actor_id'])->first();
    for ($i = 0; $i < $count; $i++) {
        $actor['id'] = (string) Str::uuid();
        $actor['subject'] = 'directory-member-'.$i;
        DB::table('app.federated_actors')->insert($actor);
        DB::table('app.tenant_memberships')->insert(array_replace($member, [
            'id' => (string) Str::uuid(), 'actor_id' => $actor['id'], 'role' => 'reader',
        ]));
    }
}

it('pages every authorized tenant beyond the old bound without duplicates or foreign tenants', function (): void {
    $tenant = (array) DB::table('app.tenants')->where('id', $this->tenant)->first();
    $member = (array) DB::table('app.tenant_memberships')->where('tenant_id', $this->tenant)->first();
    for ($i = 0; $i < 205; $i++) {
        $tenant['id'] = (string) Str::uuid();
        // Identical names do not collapse or repeat rows at a boundary.
        DB::table('app.tenants')->insert($tenant);
        DB::table('app.tenant_memberships')->insert(array_replace($member, ['id' => (string) Str::uuid(), 'tenant_id' => $tenant['id']]));
    }
    $seen = [];
    $cursor = null;
    do {
        $response = $this->getJson('/v1/tenant-directory'.($cursor === null ? '' : '?cursor='.rawurlencode($cursor)))
            ->assertOk()->assertHeader('Cache-Control', 'no-store, private')->json();
        expect(count($response['tenants']))->toBeLessThanOrEqual(50);
        $seen = [...$seen, ...array_column($response['tenants'], 'id')];
        $cursor = $response['next_cursor'];
        expect(count($seen))->toBeLessThanOrEqual(206);
    } while ($cursor !== null);
    expect($seen)->toHaveCount(206)->not->toContain($this->other)
        ->and(array_unique($seen))->toHaveCount(206);
    $this->getJson('/v1/tenants')->assertOk()->assertJsonCount(200, 'tenants')->assertJsonMissingPath('next_cursor');
});

it('pages memberships beyond 200 and preserves the published v1 projection', function (): void {
    directoryMembers($this->tenant, 205);
    $seen = [];
    $cursor = null;
    do {
        $response = $this->getJson('/v1/tenants/'.$this->tenant.'/membership-directory'.($cursor === null ? '' : '?cursor='.rawurlencode($cursor)))
            ->assertOk()->json();
        expect(count($response['memberships']))->toBeLessThanOrEqual(50);
        foreach ($response['memberships'] as $member) {
            expect($member['tenant_id'])->toBe($this->tenant);
            $seen[] = $member['id'];
        }
        $cursor = $response['next_cursor'];
        expect(count($seen))->toBeLessThanOrEqual(206);
    } while ($cursor !== null);
    expect($seen)->toHaveCount(206)->and(array_unique($seen))->toHaveCount(206);
    $this->getJson('/v1/tenants/'.$this->tenant.'/memberships')->assertOk()->assertJsonCount(200, 'memberships')->assertJsonMissingPath('next_cursor');
});

it('rejects cursor tampering expiry and reuse across views tenants or sessions', function (): void {
    // Complete a normal login: activation sessions inherit a five-minute proof
    // lifetime, shorter than a directory cursor's maximum lifetime.
    $this->token = federatedLogin($this, 'immutable-admin-subject');
    $this->withHeader('X-Console-Session', $this->token);
    directoryMembers($this->tenant, 51);
    $path = '/v1/tenants/'.$this->tenant.'/membership-directory';
    $cursor = $this->getJson($path)->assertOk()->json('next_cursor');
    $this->getJson($path.'?cursor='.rawurlencode('x'.$cursor))->assertStatus(422);
    $this->getJson('/v1/tenant-directory?cursor='.rawurlencode($cursor))->assertStatus(422);
    $otherOwner = federatedLogin($this, 'other-owner');
    tenantCommand($this, '/v1/tenants/'.$this->other.'/memberships', [
        'revision' => 0, 'subject' => 'immutable-admin-subject', 'role' => 'tenant_admin', 'state' => 'active',
        'site_id' => null, 'environment' => null, 'expires_at' => null,
    ], $otherOwner)->assertOk();
    $this->withHeader('X-Console-Session', $this->token);
    $this->getJson('/v1/tenants/'.$this->other.'/membership-directory?cursor='.rawurlencode($cursor))->assertStatus(422);
    $secondSession = federatedLogin($this, 'immutable-admin-subject');
    $this->withHeader('X-Console-Session', $secondSession)->getJson($path.'?cursor='.rawurlencode($cursor))->assertStatus(422);
    $this->withHeader('X-Console-Session', $this->token);
    $this->travel(16)->minutes();
    $this->getJson($path.'?cursor='.rawurlencode($cursor))->assertStatus(422);
});

it('rechecks revocation and role scope before returning a continued membership page', function (): void {
    directoryMembers($this->tenant, 51);
    tenantMember($this, $this->tenant, 'page-admin', 'tenant_admin');
    $token = federatedLogin($this, 'page-admin');
    $path = '/v1/tenants/'.$this->tenant.'/membership-directory';
    $cursor = $this->withHeader('X-Console-Session', $token)->getJson($path)->assertOk()->json('next_cursor');
    tenantMember($this, $this->tenant, 'page-admin', 'reader', [], 1);
    $this->withHeader('X-Console-Session', $token)->getJson($path.'?cursor='.rawurlencode($cursor))->assertForbidden();
    tenantMember($this, $this->tenant, 'page-admin', 'tenant_admin', ['site_id' => 'site-a'], 2);
    $this->withHeader('X-Console-Session', $token)->getJson($path.'?cursor='.rawurlencode($cursor))->assertForbidden();
    tenantMember($this, $this->tenant, 'page-admin', 'tenant_admin', [], 3, 'revoked');
    $this->withHeader('X-Console-Session', $token)->getJson($path.'?cursor='.rawurlencode($cursor))->assertNotFound();
});

it('denies unknown tenants missing workload identity and malformed page positions', function (): void {
    $this->getJson('/v1/tenants/'.$this->other.'/membership-directory')->assertNotFound();
    $this->getJson('/v1/tenant-directory?cursor[]=forged')->assertStatus(422);
    $this->getJson('/v1/tenant-directory?cursor='.str_repeat('a', 2049))->assertStatus(422);
    $this->withHeader('Authorization', 'Bearer invalid')->getJson('/v1/tenant-directory')->assertUnauthorized();
});
