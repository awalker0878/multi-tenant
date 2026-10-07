<?php

declare(strict_types=1);

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Inventory\Contracts\InventoryGateway;
use App\Domain\Inventory\InventoryFailure;
use Inertia\Testing\AssertableInertia as Assert;

beforeEach(function (): void {
    $this->tenant = '00000000-0000-4000-8000-000000000001';
    $this->site = '00000000-0000-4000-8000-000000000002';
    $this->key = '00000000-0000-4000-8000-000000000003';
    $this->identity = Mockery::mock(IdentityGateway::class);
    $this->identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $this->key, true));
    $this->app->instance(IdentityGateway::class, $this->identity);
    $this->inventory = Mockery::mock(InventoryGateway::class);
    $this->app->instance(InventoryGateway::class, $this->inventory);
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
    $this->base = '/tenants/'.$this->tenant.'/inventory/sites/'.$this->site.'/configuration';
});

it('renders the API owner review with cleared encrypted history', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'getPortingConfiguration', ['site' => $this->site])->andReturn(['configuration' => null]);
    $this->get($this->base)->assertOk()->assertViewHas('page', fn (array $p): bool => $p['clearHistory'] && $p['encryptHistory'])
        ->assertInertia(fn (Assert $p) => $p->component('inventory/Configuration')->where('workspace.configuration', null)->missing('session_token'));
});

it('forwards manual references and override reasons through the owner API', function (): void {
    $this->inventory->shouldReceive('call')->once()->withArgs(function ($token, $tenant, $operation, $parameters, $body, $key, $revision): bool {
        return $operation === 'savePortingConfiguration' && $parameters === ['site' => $this->site]
            && $key === $this->key && $revision === 3 && is_object($body['manual'])
            && $body['manual']->ownership_reference === 'owner-record-1'
            && $body['choices'][0]['reason'] === '';
    })->andReturn(['revision' => 4]);
    $this->post($this->base, ['operation' => 'save', 'command_key' => $this->key, 'revision' => 3,
        'configuration' => ['source_endpoint' => null, 'target_endpoint' => null, 'manual' => ['ownership_reference' => 'owner-record-1', 'backup_reference' => ''],
            'choices' => [['id' => 'compute', 'required' => true, 'interpretation' => 'observed', 'reason' => '']]]])
        ->assertRedirect($this->base)->assertSessionHas('inventory_notice');
});

it('uses the admin API pull rather than accepting browser supplied facts', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'getPortingConfiguration', ['site' => $this->site])->andReturn([]);
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'pullPortingConfiguration', ['site' => $this->site, 'endpoint' => $this->key], [], $this->key, null)->andReturn([]);
    $this->post($this->base, ['operation' => 'pull', 'command_key' => $this->key, 'endpoint_id' => $this->key, 'native_write_authorized' => true])->assertRedirect($this->base);
});

it('binds confirmation to the saved digest and revision', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'confirmPortingConfiguration', ['site' => $this->site], ['digest' => str_repeat('b', 64)], $this->key, 4)->andReturn([]);
    $this->post($this->base, ['operation' => 'confirm', 'command_key' => $this->key, 'revision' => 4, 'digest' => str_repeat('b', 64)])->assertRedirect($this->base);
});

it('keeps stale and uncertain commands reviewable', function (int $status): void {
    $this->inventory->shouldReceive('call')->once()->andThrow(new InventoryFailure($status));
    $this->from($this->base)->post($this->base, ['operation' => 'confirm', 'command_key' => $this->key, 'revision' => 4, 'digest' => str_repeat('b', 64)])
        ->assertRedirect($this->base)->assertSessionHasErrors(['command', 'inventory_status']);
})->with([412, 503]);

it('rechecks administrator access on the polling endpoint', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'getPortingConfiguration', ['site' => $this->site])->andThrow(new InventoryFailure(403));
    $this->get($this->base.'/status')->assertRedirect('/account');
});

it('requires CSRF protection for saves pulls and confirmations', function (): void {
    $this->app['env'] = 'csrf-check';
    $this->inventory->shouldNotReceive('call');
    $this->post($this->base, ['operation' => 'save'])->assertStatus(419);
});
