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
    $this->withSession(['identity.token' => str_repeat('a', 64), 'selected_tenant' => 'forged-tenant', 'role' => 'tenant_admin']);
});

afterEach(function (): void {
    unlink($this->credentialFile);
});

it('renders only current owner memberships and clears old tenant history', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants' => Http::response(['installation_administrator' => false, 'tenants' => [['id' => $this->tenant, 'name' => 'Tenant A', 'state' => 'active', 'revision' => 1, 'role' => 'reader']]]),
    ]);
    $response = $this->get('/account')->assertOk()->assertInertia(fn (Assert $page): Assert => $page->component('identity/Account')->has('tenants', 1)->where('tenants.0.id', $this->tenant)->where('canCreate', false)->missing('session_token')->missing('selected_tenant'));
    $headers = ['X-Inertia' => 'true'];
    $version = $response->viewData('page')['version'];
    if (is_string($version)) {
        $headers['X-Inertia-Version'] = $version;
    }
    $this->get('/account', $headers)->assertOk()->assertJsonPath('clearHistory', true);
});

it('never fetches administration projections for a scoped reader or trusts the browser role', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::response(['tenant' => ['id' => $this->tenant, 'name' => 'Tenant A', 'state' => 'active', 'revision' => 1], 'membership' => ['role' => 'reader', 'site_id' => 'site-a', 'environment' => 'development']]),
    ]);
    $this->get('/tenants/'.$this->tenant)->assertOk()->assertInertia(fn (Assert $page): Assert => $page->component('tenancy/Tenant')->where('canAdminister', false)->has('memberships', 0)->where('quota', null));
    Http::assertSentCount(2);
});

it('removes a revoked or guessed tenant from the journey without rendering stale props', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::response(['error' => 'not_found'], 404),
    ]);
    $this->get('/tenants/'.$this->tenant)->assertRedirect('/account')->assertSessionHas('tenant_notice');
});

it('keeps command identity stable and sends only approved membership fields to its owner', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant.'/memberships' => Http::response(['error' => 'forbidden'], 403),
    ]);
    $key = '550e8400-e29b-41d4-a716-446655440002';
    $this->post('/tenants/'.$this->tenant.'/memberships', ['command_key' => $key, 'revision' => 0, 'subject' => 'some-subject', 'role' => 'tenant_admin', 'state' => 'active', 'site_id' => null, 'environment' => null, 'expires_at' => null, 'actor_id' => 'forged-admin', 'tenant_id' => 'other-tenant'])
        ->assertRedirect('/account');
    Http::assertSent(fn (OutboundRequest $request): bool => $request->method() === 'POST' && $request->hasHeader('Idempotency-Key', $key)
        && ! isset($request['actor_id']) && ! isset($request['tenant_id']) && ! isset($request['command_key']));
});

it('requires the real CSRF middleware on all tenant writes', function (string $suffix): void {
    $this->app['env'] = 'csrf-check';
    Http::fake();
    $path = $suffix === '' ? '/tenants' : '/tenants/'.$this->tenant.'/'.$suffix;
    $this->post($path)->assertStatus(419);
    Http::assertNothingSent();
})->with(['', 'memberships', 'quota', 'state']);
