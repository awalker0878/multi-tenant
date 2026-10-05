<?php

declare(strict_types=1);

use App\Application\Notifications\Contracts\NotificationHints;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia as Assert;

beforeEach(function (): void {
    $this->credentialFile = tempnam(sys_get_temp_dir(), 'p02-console-');
    file_put_contents($this->credentialFile, bin2hex(random_bytes(32)));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $this->credentialFile]);
    Http::preventStrayRequests();
    $this->actor = ['identity' => ['subject' => '550e8400-e29b-41d4-a716-446655440000', 'kind' => 'federated', 'password_change_required' => false, 'permissions' => ['identity.logout']]];
    $this->tenant = '550e8400-e29b-41d4-a716-446655440001';
    $this->withSession(['identity.token' => str_repeat('a', 64), 'selected_tenant' => 'other-tenant', 'role' => 'tenant_admin']);
    $this->hints = new class implements NotificationHints
    {
        public array $lookups = [];

        public bool $fail = false;

        public function current(string $tenant): ?string
        {
            $this->lookups[] = $tenant;
            if ($this->fail) {
                throw new RuntimeException('private database connection details');
            }

            return '550e8400-e29b-41d4-a716-446655440009';
        }
    };
    app()->instance(NotificationHints::class, $this->hints);
});

afterEach(function (): void {
    unlink($this->credentialFile);
});

it('rechecks current owner authority on every poll and returns only an opaque cursor', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::sequence()
            ->push(['membership' => ['role' => 'tenant_admin', 'site_id' => null, 'environment' => null]])->push(['error' => 'not_found'], 404),
    ]);
    $path = '/tenants/'.$this->tenant.'/notification-status?tenant_id=forged&role=tenant_admin';
    $this->getJson($path)->assertOk()->assertExactJson(['cursor' => '550e8400-e29b-41d4-a716-446655440009'])->assertHeader('Cache-Control', 'no-store, private');
    $this->getJson($path)->assertNotFound();
    expect($this->hints->lookups)->toBe([$this->tenant]);
    Http::assertSentCount(4);
});

it('denies readers and scoped administrators before the hint lookup', function (string $role, ?string $site, ?string $environment): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::response(['membership' => ['role' => $role, 'site_id' => $site, 'environment' => $environment]]),
    ]);
    $this->getJson('/tenants/'.$this->tenant.'/notification-status')->assertForbidden();
    expect($this->hints->lookups)->toBe([]);
})->with([['reader', null, null], ['tenant_admin', 'site-a', null], ['tenant_admin', null, 'production']]);

it('does not expose a hint when the owner or session authority is unavailable', function (int $status): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::response(['error' => 'unavailable'], $status),
    ]);
    $this->getJson('/tenants/'.$this->tenant.'/notification-status')->assertStatus($status);
    expect($this->hints->lookups)->toBe([]);
})->with([401, 403, 404, 503]);

it('reports hint storage outages without exposing database details', function (): void {
    $this->hints->fail = true;
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::response(['membership' => ['role' => 'tenant_admin', 'site_id' => null, 'environment' => null]]),
    ]);
    $this->getJson('/tenants/'.$this->tenant.'/notification-status')->assertStatus(503)
        ->assertExactJson(['error' => 'notifications_unavailable'])->assertHeader('Cache-Control', 'no-store, private');
});

it('preserves owner-backed administration while marking unavailable notifications explicitly', function (): void {
    $this->hints->fail = true;
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->actor),
        'governance.example.test/v1/tenants/'.$this->tenant => Http::response([
            'tenant' => ['id' => $this->tenant, 'name' => 'Tenant A', 'state' => 'active', 'revision' => 1],
            'membership' => ['role' => 'tenant_admin', 'site_id' => null, 'environment' => null],
        ]),
        'governance.example.test/v1/tenants/'.$this->tenant.'/membership-directory' => Http::response(['memberships' => []]),
        'governance.example.test/v1/tenants/'.$this->tenant.'/quota' => Http::response(['revision' => 0, 'entitlement' => null]),
    ]);
    $this->get('/tenants/'.$this->tenant)->assertOk()->assertInertia(fn (Assert $page): Assert => $page->component('tenancy/Tenant')
        ->where('canAdminister', true)->where('notificationCursor', null)->where('notificationsAvailable', false));
});
