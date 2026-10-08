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
    $identity = Mockery::mock(IdentityGateway::class);
    $identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $this->key, true));
    $this->app->instance(IdentityGateway::class, $identity);
    $this->inventory = Mockery::mock(InventoryGateway::class);
    $this->app->instance(InventoryGateway::class, $this->inventory);
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
    $this->base = '/tenants/'.$this->tenant.'/inventory/sites/'.$this->site.'/operator-inputs';
});

it('renders operator inputs through current site authority with encrypted cleared history', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'getOperatorInputs', ['site' => $this->site])->andReturn(['record' => null]);
    $this->get($this->base)->assertOk()->assertViewHas('page', fn (array $p): bool => $p['clearHistory'] && $p['encryptHistory'])
        ->assertInertia(fn (Assert $p) => $p->component('inventory/OperatorInputs')->where('workspace.record', null)->missing('session_token'));
});

it('forwards zero targets and safe references without inventing empty values', function (): void {
    $this->inventory->shouldReceive('call')->once()->withArgs(function ($token, $tenant, $operation, $parameters, $body, $key, $revision): bool {
        return $tenant === $this->tenant && $operation === 'saveOperatorInputs' && $parameters === ['site' => $this->site]
            && $key === $this->key && $revision === 2 && $body['configuration_digest'] === null
            && is_object($body['values']) && $body['values']->max_outage_seconds === 0
            && $body['values']->source_writer_ref === 'vault:source/execution'
            && ! property_exists($body['values'], 'target_writer_ref');
    })->andReturn(['revision' => 3]);
    $this->post($this->base, ['command_key' => $this->key, 'revision' => 2, 'input' => ['configuration_digest' => null, 'values' => ['max_outage_seconds' => 0, 'source_writer_ref' => 'vault:source/execution', 'target_writer_ref' => '']]])
        ->assertRedirect($this->base)->assertSessionHas('inventory_notice');
});

it('preserves an empty object on the wire and reauthorizes packet downloads', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'getOperatorInputs', ['site' => $this->site])->andReturn(['record' => ['values' => []], 'native_write_authorized' => false]);
    $response = $this->get($this->base.'/download')->assertOk()->assertHeader('Content-Disposition', 'attachment; filename="operator-inputs.json"')
        ->assertJsonPath('qualification_status', 'not_established')->assertJsonPath('native_write_authorized', false);
    expect($response->headers->get('Cache-Control'))->toContain('no-store');
    expect(json_decode($response->getContent())->record->values)->toBeInstanceOf(stdClass::class);
});

it('does not export a draft that has never been saved', function (): void {
    $this->inventory->shouldReceive('call')->once()->andReturn(['record' => null]);
    $this->get($this->base.'/download')->assertNotFound();
});

it('rechecks access for polling and download', function (string $suffix): void {
    $this->inventory->shouldReceive('call')->once()->andThrow(new InventoryFailure(403));
    $this->get($this->base.$suffix)->assertRedirect('/account');
})->with(['/status', '/download']);

it('preserves stale and uncertain saves for explicit recovery', function (int $status): void {
    $this->inventory->shouldReceive('call')->once()->andThrow(new InventoryFailure($status));
    $this->from($this->base)->post($this->base, ['command_key' => $this->key, 'revision' => 2, 'input' => ['configuration_digest' => null, 'values' => []]])
        ->assertRedirect($this->base)->assertSessionHasErrors(['command', 'inventory_status']);
})->with([412, 503]);

it('rejects invented API facts at the browser boundary', function (): void {
    $this->inventory->shouldNotReceive('call');
    $this->from($this->base)->post($this->base, ['command_key' => $this->key, 'input' => ['configuration_digest' => null, 'values' => [], 'api_version' => 'invented']])
        ->assertSessionHasErrors('input');
});

it('protects operator input saves with CSRF verification', function (): void {
    $this->app['env'] = 'csrf-check';
    $this->inventory->shouldNotReceive('call');
    $this->post($this->base, ['command_key' => $this->key])->assertStatus(419);
});
