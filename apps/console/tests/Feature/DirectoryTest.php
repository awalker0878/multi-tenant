<?php

declare(strict_types=1);

use Illuminate\Http\Client\Request as OutboundRequest;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia as Assert;

beforeEach(function (): void {
    $this->credentialFile = tempnam(sys_get_temp_dir(), 'p02-console-');
    file_put_contents($this->credentialFile, bin2hex(random_bytes(32)));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $this->credentialFile]);
    Http::preventStrayRequests();
    $this->actor = ['identity' => ['subject' => '550e8400-e29b-41d4-a716-446655440000', 'kind' => 'federated', 'password_change_required' => false, 'permissions' => ['identity.logout']]];
    $this->tenant = '550e8400-e29b-41d4-a716-446655440001';
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
});

afterEach(function (): void {
    unlink($this->credentialFile);
});

it('forwards only an encoded cursor and renders the next owner-provided tenant page', function (): void {
    $cursor = 'opaque+cursor/=with&characters';
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenant-directory?cursor='.rawurlencode($cursor) => Http::response([
            'tenants' => [['id' => $this->tenant, 'name' => 'Later tenant', 'state' => 'active', 'revision' => 1, 'role' => 'reader']],
            'installation_administrator' => false, 'next_cursor' => 'next-owner-cursor',
        ]),
    ]);
    $this->get('/account?cursor='.rawurlencode($cursor).'&role=tenant_admin&tenant_id=forged')
        ->assertOk()->assertInertia(fn (Assert $page): Assert => $page->component('identity/Account')
        ->where('tenants.0.name', 'Later tenant')->where('continued', true)->where('nextCursor', 'next-owner-cursor')->where('canCreate', false));
    Http::assertSent(fn (OutboundRequest $request): bool => str_contains($request->url(), '/tenant-directory?cursor='.rawurlencode($cursor))
        && ! str_contains($request->url(), 'role=') && ! str_contains($request->url(), 'tenant_id='));
});

it('renders continued membership pages only after current tenant authority', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::response([
            'tenant' => ['id' => $this->tenant, 'name' => 'Tenant A', 'state' => 'active', 'revision' => 1],
            'membership' => ['role' => 'tenant_admin', 'site_id' => null, 'environment' => null],
        ]),
        'governance.example.test/v1/tenants/'.$this->tenant.'/membership-directory?cursor=opaque' => Http::response(['memberships' => [], 'next_cursor' => null]),
        'governance.example.test/v1/tenants/'.$this->tenant.'/quota' => Http::response(['revision' => 0, 'entitlement' => null]),
    ]);
    $this->get('/tenants/'.$this->tenant.'?cursor=opaque')->assertOk()->assertInertia(fn (Assert $page): Assert => $page->component('tenancy/Tenant')
        ->where('canAdminister', true)->where('continued', true)->where('nextCursor', null)->has('memberships', 0));
});

it('restarts invalid or expired page links without rendering remembered data', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenant-directory?cursor=expired' => Http::response(['error' => 'invalid_cursor'], 422),
    ]);
    $this->get('/account?cursor=expired')->assertRedirect('/account')->assertSessionHas('tenant_notice');
    $this->get('/account?cursor[]=forged')->assertRedirect('/account');
    $this->get('/account?cursor='.str_repeat('x', 2049))->assertRedirect('/account');
    Http::assertSentCount(4);
});

it('does not downgrade owner unavailability to an empty successful tenant list', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenant-directory*' => Http::response(['error' => 'unavailable'], 503),
    ]);
    $this->get('/account?cursor=opaque')->assertStatus(503);
});

it('denies guessed and revoked tenant continuations before retrieving memberships', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::response(['error' => 'not_found'], 404),
    ]);
    $this->get('/tenants/'.$this->tenant.'?cursor=previously-valid')->assertRedirect('/account');
    Http::assertSentCount(2);
});
