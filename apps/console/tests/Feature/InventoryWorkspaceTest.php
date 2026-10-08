<?php

declare(strict_types=1);

use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Inventory\Contracts\InventoryGateway;
use App\Domain\Inventory\InventoryFailure;
use App\Infrastructure\Inventory\InventoryClient;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia as Assert;

beforeEach(function (): void {
    $this->tenant = '00000000-0000-4000-8000-000000000001';
    $this->site = '00000000-0000-4000-8000-000000000002';
    $this->endpoint = '00000000-0000-4000-8000-000000000003';
    $this->identity = Mockery::mock(IdentityGateway::class);
    $this->identity->shouldReceive('current')->andReturn(new ConsoleActor(false, '00000000-0000-4000-8000-000000000004', true));
    $this->app->instance(IdentityGateway::class, $this->identity);
    $this->inventory = Mockery::mock(InventoryGateway::class);
    $this->app->instance(InventoryGateway::class, $this->inventory);
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
    $this->base = '/tenants/'.$this->tenant.'/inventory/sites/'.$this->site;
});

it('renders scoped sites with encrypted cleared history and no credentials', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'listSites', [], [], null, null, null)
        ->andReturn(['items' => [['site_id' => $this->site]], 'next_cursor' => null]);
    $this->get('/tenants/'.$this->tenant.'/inventory')->assertOk()->assertViewHas('page', fn (array $p): bool => $p['clearHistory'] === true && $p['encryptHistory'] === true)
        ->assertInertia(fn (Assert $p) => $p->component('inventory/Index')->has('sites.items', 1)->missing('session_token')->missing('credential_file'));
});

it('does not request protected enrollment policies for a reader', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'listEndpoints', ['site' => $this->site], [], null, null, null)->andReturn(['items' => [], 'next_cursor' => null]);
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'siteHealth', ['site' => $this->site])->andReturn(['items' => [], 'observed_at' => 0]);
    $this->inventory->shouldReceive('permitted')->twice()->andReturn(false);
    $this->get($this->base)->assertOk()->assertInertia(fn (Assert $p) => $p->component('inventory/Site')->where('canAdminister', false)->where('policies', []));
});

it('preserves command identity on a stale or uncertain result', function (int $status): void {
    $key = '00000000-0000-4000-8000-000000000005';
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'revokeEndpoint', ['site' => $this->site, 'endpoint' => $this->endpoint], [], $key, 2)->andThrow(new InventoryFailure($status));
    $this->from($this->base)->post($this->base.'/commands', ['operation' => 'revokeEndpoint', 'command_key' => $key, 'endpoint_id' => $this->endpoint, 'revision' => 2, 'tenant_id' => 'forged'])
        ->assertRedirect($this->base)->assertSessionHasErrors(['command', 'inventory_status']);
    expect(session('errors')->getBag('default')->first('inventory_status'))->toBe((string) $status);
})->with([412, 503, 429]);

it('redirects revoked or guessed site access without displaying inventory', function (): void {
    $this->inventory->shouldReceive('call')->once()->andThrow(new InventoryFailure(403));
    $this->get($this->base)->assertRedirect('/account')->assertSessionHas('tenant_notice');
});

it('uses actual CSRF middleware for enrollment and discovery commands', function (): void {
    $this->app['env'] = 'csrf-check';
    $this->inventory->shouldNotReceive('call');
    $this->post($this->base.'/commands')->assertStatus(419);
});

it('confirms Catalogue revision access before recording a matching proposal', function (): void {
    $catalogue = Mockery::mock(CatalogueGateway::class);
    $this->app->instance(CatalogueGateway::class, $catalogue);
    $id = '00000000-0000-4000-8000-000000000006';
    $catalogue->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'getRevision', ['application' => $id, 'revision' => $id], [], null, null, $id)->andReturn([]);
    $this->inventory->shouldReceive('call')->once()->andReturn(['match_id' => $id, 'state' => 'proposed_unverified', 'ownership_granted' => false]);
    $this->post($this->base.'/commands', ['operation' => 'proposeMatch', 'command_key' => $id, 'endpoint_id' => $this->endpoint, 'resource_id' => $id, 'application_id' => $id, 'intent_revision' => $id, 'environment' => $id, 'generation_id' => $id])
        ->assertRedirect($this->base.'/generations/'.$id)->assertSessionHas('inventory_notice');
});

it('binds separate workload and current delegation and rejects additional response data', function (): void {
    $governance = tempnam(sys_get_temp_dir(), 'p04-gov-');
    $inventory = tempnam(sys_get_temp_dir(), 'p04-inv-');
    file_put_contents($governance, str_repeat('b', 64));
    file_put_contents($inventory, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $governance, 'inventory.url' => 'https://inventory.example.test', 'inventory.credential_file' => $inventory, 'inventory.ca_file' => $inventory]);
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'inventory', 'authority_use' => 'request_bound'], 201),
        'inventory.example.test/*' => Http::sequence()->push(['items' => [], 'next_cursor' => null])->push(['items' => [], 'next_cursor' => null, 'secret' => 'unexpected'])]);
    try {
        $client = app(InventoryClient::class);
        expect($client->call(str_repeat('a', 64), $this->tenant, 'listSites'))->toBe(['items' => [], 'next_cursor' => null]);
        Http::assertSent(fn ($r) => str_contains($r->url(), 'inventory.example.test') && $r->hasHeader('Authorization', 'Bearer '.str_repeat('c', 64)) && $r->hasHeader('X-Actor-Delegation', str_repeat('d', 64)) && ! $r->hasHeader('X-Console-Session'));
        expect(fn () => $client->call(str_repeat('a', 64), $this->tenant, 'listSites'))->toThrow(InventoryFailure::class);
    } finally {
        unlink($governance);
        unlink($inventory);
    }
});
