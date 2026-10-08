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
    $this->base = '/tenants/'.$this->tenant.'/inventory/sites/'.$this->site.'/migration';
});

it('reads the current profile review and clears encrypted history', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'getMigrationReview', ['site' => $this->site])->andReturn(['review' => null]);
    $this->get($this->base)->assertOk()->assertViewHas('page', fn (array $p): bool => $p['clearHistory'] && $p['encryptHistory'])
        ->assertInertia(fn (Assert $p) => $p->component('inventory/Migration')->where('workspace.review', null)->missing('session_token'));
});

it('forwards only the revision and digest for confirmation', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'confirmMigrationReview', ['site' => $this->site], ['digest' => str_repeat('b', 64)], $this->key, 4)->andReturn([]);
    $this->post($this->base, ['operation' => 'confirm', 'command_key' => $this->key, 'revision' => 4, 'digest' => str_repeat('b', 64), 'native_write_authorized' => true])->assertRedirect($this->base);
});

it('preserves stale and uncertain command outcomes for exact retry', function (int $status): void {
    $this->inventory->shouldReceive('call')->once()->andThrow(new InventoryFailure($status));
    $this->from($this->base)->post($this->base, ['operation' => 'confirm', 'command_key' => $this->key, 'revision' => 4, 'digest' => str_repeat('b', 64)])
        ->assertRedirect($this->base)->assertSessionHasErrors(['command', 'inventory_status']);
})->with([412, 503]);

it('rejects manual replacement of observed profiles', function (): void {
    $this->inventory->shouldNotReceive('call');
    $this->from($this->base)->post($this->base, ['operation' => 'save', 'command_key' => $this->key,
        'review' => ['source_profile_id' => $this->key, 'target_profile_id' => $this->key, 'method' => 'VM_COLD_EXPORT', 'datasets' => [], 'owner_inputs' => [], 'objectives' => [], 'overrides' => [], 'source' => ['cpu' => 32]]])
        ->assertRedirect($this->base)->assertSessionHasErrors('review');
});

it('forwards VMware destination mappings intact for authoritative inventory validation', function (): void {
    $destination = [
        'platform' => 'vmware', 'project_id' => 'datacenter-1', 'vcenter_uuid' => $this->site,
        'folder_id' => 'group-v3', 'resource_pool_id' => 'resgroup-2', 'host_id' => 'host-1',
        'datastore_id' => 'datastore-1', 'guest_id' => 'rhel9_64Guest', 'hardware_version' => 'vmx-21',
        'firmware' => 'efi', 'disks' => [['source_key' => 0, 'index' => 0]],
        'nics' => [['source_key' => 0, 'quarantine_network_id' => 'network-1', 'production_network_id' => 'network-2']],
    ];
    $review = ['source_profile_id' => $this->key, 'target_profile_id' => $this->site,
        'method' => 'VM_COLD_EXPORT', 'datasets' => [['id' => $this->key]],
        'owner_inputs' => array_fill_keys(['application_consistency', 'quiesce', 'health', 'delta_protocol', 'cutover', 'rollback', 'backup', 'owner'], 'reviewed'),
        'objectives' => ['max_outage_seconds' => 0], 'overrides' => [], 'destination' => $destination];
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant,
        'saveMigrationReview', ['site' => $this->site], $review, $this->key, null)->andReturn([]);
    $this->post($this->base, ['operation' => 'save', 'command_key' => $this->key, 'review' => $review])
        ->assertRedirect($this->base)->assertSessionHasNoErrors();
});

it('rechecks access on polling and applies csrf to migration writes', function (): void {
    $this->inventory->shouldReceive('call')->once()->andThrow(new InventoryFailure(403));
    $this->get($this->base.'/status')->assertRedirect('/account');
    $this->app['env'] = 'csrf-check';
    $this->post($this->base, ['operation' => 'save'])->assertStatus(419);
});

it('opens a VM-specific review without a site-wide latest review collision', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->tenant, 'getVmMigrationReview', ['site' => $this->site, 'profile' => $this->key])->andReturn(['review' => null]);
    $this->get($this->base.'/profiles/'.$this->key)->assertOk()->assertInertia(fn (Assert $p) => $p->component('inventory/Migration')->where('profileId', $this->key));
});
