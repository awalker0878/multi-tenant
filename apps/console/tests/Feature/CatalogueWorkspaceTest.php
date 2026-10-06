<?php

declare(strict_types=1);

use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Domain\Catalogue\CatalogueFailure;
use App\Infrastructure\Catalogue\CatalogueClient;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia as Assert;

beforeEach(function (): void {
    $this->tenant = '00000000-0000-4000-8000-000000000001';
    $this->actor = '00000000-0000-4000-8000-000000000002';
    $this->applicationId = '00000000-0000-4000-8000-000000000003';
    $this->identity = Mockery::mock(IdentityGateway::class);
    $this->identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $this->actor, true));
    $this->app->instance(IdentityGateway::class, $this->identity);
    $this->gateway = Mockery::mock(CatalogueGateway::class);
    $this->app->instance(CatalogueGateway::class, $this->gateway);
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
});

it('renders the bounded owner list and no bearer or implicit tenant context', function (): void {
    $this->gateway->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'listApplications', [], [], null, null, null, null)
        ->andReturn(['applications' => [['id' => $this->applicationId, 'name' => '<script>intent</script>', 'etag' => '"'.$this->applicationId.':1"']], 'next_cursor' => null]);
    $this->gateway->shouldReceive('permitted')->once()->andReturn(true);
    $this->get('/tenants/'.$this->tenant.'/applications')->assertOk()->assertViewHas('page', fn (array $page): bool => $page['encryptHistory'] === true && $page['clearHistory'] === true)
        ->assertInertia(fn (Assert $p) => $p->component('catalogue/Index')->has('applications', 1)->missing('session_token')->missing('delegation_token')->where('tenantId', $this->tenant));
});

it('preserves exact command identity and resolves stale edits through the Inertia error bag', function (): void {
    $key = '00000000-0000-4000-8000-000000000005';
    $this->gateway->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'publishRevision', ['application' => $this->applicationId], ['intent' => ['environment' => ['id' => 'environment']]], $key, '"'.$this->applicationId.':1"')
        ->andThrow(new CatalogueFailure(412, 'stale_revision', 'etag'));
    $this->from('/tenants/'.$this->tenant.'/applications/'.$this->applicationId.'/edit')->post('/tenants/'.$this->tenant.'/applications/'.$this->applicationId.'/revisions', [
        'name' => 'Permit', 'command_key' => $key, 'etag' => '"'.$this->applicationId.':1"', 'intent_json' => '{"environment":{"id":"environment"}}', 'actor_id' => 'forged',
    ])->assertRedirect()->assertSessionHasErrors(['intent_json', 'catalogue_status']);
    expect(session('errors')->getBag('default')->first('catalogue_status'))->toBe('412');
    expect(session()->getOldInput('intent_json'))->toBeNull();
});

it('keeps uncertainty explicit instead of silently issuing a replacement command', function (): void {
    $this->gateway->shouldReceive('call')->once()->andThrow(new CatalogueFailure(503));
    $this->from('/tenants/'.$this->tenant.'/applications/create')->post('/tenants/'.$this->tenant.'/applications', ['name' => 'Permit', 'command_key' => '00000000-0000-4000-8000-000000000005', 'intent_json' => '{}'])
        ->assertRedirect()->assertSessionHasErrors(['catalogue_status']);
    expect(session('errors')->getBag('default')->first('catalogue_status'))->toBe('503');
});

it('rejects invalid imports before calling a domain owner', function (): void {
    $this->gateway->shouldNotReceive('call');
    $this->post('/tenants/'.$this->tenant.'/applications', ['name' => 'Permit', 'command_key' => '00000000-0000-4000-8000-000000000005', 'intent_json' => '<html>'])->assertSessionHasErrors('intent_json');
});

it('applies the real CSRF middleware to application and reference writes', function (string $suffix): void {
    $this->app['env'] = 'csrf-check';
    $this->gateway->shouldNotReceive('call');
    $this->post('/tenants/'.$this->tenant.'/'.$suffix)->assertStatus(419);
})->with(['applications', 'catalogue-references']);

it('the generated client binds workload and delegated actor and validates actual returned wire schema', function (): void {
    $governance = tempnam(sys_get_temp_dir(), 'p03-gov-');
    $catalogue = tempnam(sys_get_temp_dir(), 'p03-cat-');
    file_put_contents($governance, str_repeat('b', 64));
    file_put_contents($catalogue, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $governance,
        'catalogue.url' => 'https://catalogue.example.test', 'catalogue.credential_file' => $catalogue]);
    Http::preventStrayRequests();
    Http::fake([
        'governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'catalogue', 'authority_use' => 'request_bound'], 201),
        'catalogue.example.test/*' => Http::sequence()->push(['applications' => [], 'next_cursor' => null])->push(['applications' => [], 'next_cursor' => null, 'secret' => 'unexpected']),
    ]);
    try {
        $client = app(CatalogueClient::class);
        expect($client->call(str_repeat('a', 64), $this->tenant, 'listApplications'))->toBe(['applications' => [], 'next_cursor' => null]);
        Http::assertSent(fn ($r) => str_contains($r->url(), 'catalogue.example.test') && $r->hasHeader('Authorization', 'Bearer '.str_repeat('c', 64)) && $r->hasHeader('X-Actor-Delegation', str_repeat('d', 64)) && ! $r->hasHeader('X-Console-Session'));
        expect(fn () => $client->call(str_repeat('a', 64), $this->tenant, 'listApplications'))->toThrow(CatalogueFailure::class);
    } finally {
        unlink($governance);
        unlink($catalogue);
    }
});
