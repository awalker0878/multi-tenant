<?php

declare(strict_types=1);

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Inventory\Contracts\InventoryGateway;
use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Planning\PlanningFailure;
use App\Infrastructure\Planning\PlanningClient;
use Illuminate\Support\Facades\Http;

beforeEach(function (): void {
    $this->id = '00000000-0000-4000-8000-000000000001';
    $this->member = '00000000-0000-5000-8000-000000000002';
    $this->base = '/tenants/'.$this->id.'/inventory/sites/'.$this->id.'/migration-fleet';
    $identity = Mockery::mock(IdentityGateway::class);
    $identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $this->id, true));
    $this->app->instance(IdentityGateway::class, $identity);
    $this->inventory = Mockery::mock(InventoryGateway::class);
    $this->planning = Mockery::mock(PlanningGateway::class);
    $this->app->instance(InventoryGateway::class, $this->inventory);
    $this->app->instance(PlanningGateway::class, $this->planning);
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
    $this->detail = ['group' => ['revision' => 1, 'digest' => str_repeat('b', 64), 'input' => ['application_id' => $this->id, 'environment_id' => $this->id]],
        'members' => [['candidate' => ['resource_id' => $this->member], 'holds' => [], 'preparation' => ['site_id' => $this->id, 'review' => ['revision' => 2, 'digest' => str_repeat('c', 64)], 'disks' => []]]]];
});

it('prepares each member from the current server group and ignores browser disk claims', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, 'getMigrationGroup', ['site' => $this->id, 'group' => $this->id])->andReturn($this->detail);
    $this->planning->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, $this->id, $this->id, 'POST', 'migration-preparations', [$this->id], $this->detail['members'][0]['preparation'])->andReturn(['binding' => ['method' => 'VM_COLD_EXPORT'], 'native_write_authorized' => false]);
    $this->postJson($this->base.'/groups/'.$this->id.'/prepare', ['revision' => 1, 'digest' => str_repeat('b', 64), 'resource_id' => $this->member, 'disks' => ['forged']])->assertOk()->assertJsonPath('native_write_authorized', false)->assertHeader('Cache-Control', 'no-store, private');
});

it('holds stale groups, blocked members and foreign members before Planning', function (string $fault, int $status): void {
    if ($fault === 'stale') {
        $this->detail['group']['revision'] = 2;
    } elseif ($fault === 'held') {
        $this->detail['members'][0]['holds'] = ['source_profile_stale'];
    } else {
        $this->detail['members'] = [];
    }
    $this->inventory->shouldReceive('call')->once()->andReturn($this->detail);
    $this->planning->shouldNotReceive('call');
    $this->postJson($this->base.'/groups/'.$this->id.'/prepare', ['revision' => 1, 'digest' => str_repeat('b', 64), 'resource_id' => $this->member])->assertStatus($status);
})->with([['stale', 412], ['held', 409], ['foreign', 404]]);

it('saves UUID5 inventory members with the exact optimistic revision and command key', function (): void {
    $selection = ['name' => 'Wave 1', 'application_id' => $this->id, 'environment_id' => $this->id, 'target_profile_id' => $this->id, 'format' => 'raw', 'resource_ids' => [$this->member]];
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, 'updateMigrationGroup', ['site' => $this->id, 'group' => $this->id], $selection, $this->id, 1)->andReturn(['id' => $this->id]);
    $this->post($this->base.'/groups/'.$this->id, ['command_key' => $this->id, 'revision' => 1, 'selection' => $selection])->assertRedirect($this->base.'/groups/'.$this->id);
});

it('queues scoped native API collection without starting a migration', function (): void {
    $this->inventory->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, 'requestDiscovery', ['site' => $this->id, 'endpoint' => $this->id], [], $this->id)->andReturn([]);
    $this->planning->shouldNotReceive('call');
    $this->post($this->base.'/refresh', ['endpoint_id' => $this->id, 'command_key' => $this->id])->assertRedirect($this->base);
});

it('finds scoped complete plan choices using the server reviewed member', function (): void {
    $this->inventory->shouldReceive('call')->once()->andReturn($this->detail);
    $this->planning->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, $this->id, $this->id, 'POST', 'migration-plan-options', [$this->id], $this->detail['members'][0]['preparation'])->andReturn(['items' => [], 'native_write_authorized' => false]);
    $this->postJson($this->base.'/groups/'.$this->id.'/prepare', ['operation' => 'options', 'revision' => 1, 'digest' => str_repeat('b', 64), 'resource_id' => $this->member])->assertOk()->assertJsonPath('items', []);
});

it('creates a complete proposal with the exact retry key and ignores browser native facts', function (): void {
    $this->inventory->shouldReceive('call')->twice()->andReturn($this->detail);
    $this->planning->shouldReceive('call')->twice()->with(str_repeat('a', 64), $this->id, $this->id, $this->id, 'POST', 'migration-plans', [$this->id], $this->detail['members'][0]['preparation'] + ['base_plan_id' => $this->id, 'recipe_id' => $this->member], $this->id)->andReturn(['id' => $this->id, 'kind' => 'plan', 'native_write_authorized' => false]);
    $command = ['operation' => 'compose', 'revision' => 1, 'digest' => str_repeat('b', 64), 'resource_id' => $this->member, 'base_plan_id' => $this->id, 'recipe_id' => $this->member, 'command_key' => $this->id, 'native_write_authorized' => true, 'disks' => ['forged']];
    $this->postJson($this->base.'/groups/'.$this->id.'/prepare', $command)->assertOk()->assertJsonPath('native_write_authorized', false);
    $this->postJson($this->base.'/groups/'.$this->id.'/prepare', $command)->assertOk();
});

it('enforces real csrf on bulk preparation', function (): void {
    $this->app['env'] = 'csrf-check';
    $this->inventory->shouldNotReceive('call');
    $this->planning->shouldNotReceive('call');
    $this->post($this->base.'/groups/'.$this->id.'/prepare')->assertStatus(419);
});

it('uses migration delegation and distinguishes denied authority from a definite hold', function (int $status, array $response, int $expected): void {
    $gov = tempnam(sys_get_temp_dir(), 'p08-gov-');
    $plan = tempnam(sys_get_temp_dir(), 'p08-plan-');
    file_put_contents($gov, str_repeat('b', 64));
    file_put_contents($plan, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $gov, 'planning.url' => 'https://planning.example.test', 'planning.credential_file' => $plan, 'planning.ca_file' => $plan]);
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'planning', 'authority_use' => 'request_bound'], 201), 'planning.example.test/*' => Http::response($response, $status)]);
    try {
        try {
            app(PlanningClient::class)->call(str_repeat('a', 64), $this->id, $this->id, $this->id, 'POST', 'migration-preparations', [$this->id], $this->detail['members'][0]['preparation']);
            $this->fail('Planning must reject this response.');
        } catch (PlanningFailure $error) {
            expect($error->status)->toBe($expected);
        }
        Http::assertSent(fn ($r) => str_contains($r->url(), '/migration-preparations') && $r->hasHeader('X-Actor-Delegation', str_repeat('d', 64)) && ! $r->hasHeader('X-Planning-Delegations') && ! $r->hasHeader('X-Console-Session'));
    } finally {
        unlink($gov);
        unlink($plan);
    }
})->with([
    [200, ['binding' => [], 'native_write_authorized' => true], 503],
    [423, ['error' => 'migration_recipe_changed'], 423],
]);
