<?php

declare(strict_types=1);

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Planning\Contracts\PlanningGateway;

it('reads scoped support without forwarding browser qualification claims', function (): void {
    $id = '00000000-0000-4000-8000-000000000001';
    $identity = Mockery::mock(IdentityGateway::class);
    $identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $id, true));
    $this->app->instance(IdentityGateway::class, $identity);
    $planning = Mockery::mock(PlanningGateway::class);
    $planning->shouldReceive('call')->once()->with(str_repeat('a', 64), $id, $id, $id, 'POST', 'migration-support', [$id], ['site_id' => $id])->andReturn(['directions' => [], 'native_write_authorized' => false]);
    $this->app->instance(PlanningGateway::class, $planning);
    $this->withSession(['identity.token' => str_repeat('a', 64)])->getJson('/tenants/'.$id.'/applications/'.$id.'/environments/'.$id.'/planning/migration-support/'.$id.'/status?native_qualified=true')->assertOk()->assertJsonPath('support.native_write_authorized', false)->assertHeader('Cache-Control', 'no-store, private');
});


it('shows only current application-scoped native flow choices from Planning', function (): void {
    $id = '00000000-0000-4000-8000-000000000001';
    $identity = Mockery::mock(IdentityGateway::class);
    $identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $id, true));
    $this->app->instance(IdentityGateway::class, $identity);
    $planning = Mockery::mock(PlanningGateway::class);
    $flow = [
        'context_sha256' => str_repeat('a', 64), 'revision' => 0,
        'expires_at' => 2_000_000_120, 'choices' => [], 'selections' => [], 'omissions' => [],
        'holds' => ['source_flow_required'], 'status' => 'held',
        'native_write_authorized' => false,
    ];
    $planning->shouldReceive('call')->once()->with(
        str_repeat('a', 64), $id, $id, $id, 'POST', 'migration-flow-choices',
        [$id], ['site_id' => $id],
    )->andReturn($flow);
    $this->app->instance(PlanningGateway::class, $planning);
    $this->withSession(['identity.token' => str_repeat('a', 64)])
        ->getJson('/tenants/'.$id.'/applications/'.$id.'/environments/'.$id.'/planning/migration-support/'.$id.'/flow-choices')
        ->assertOk()->assertJsonPath('flow_choices.context_sha256', str_repeat('a', 64))
        ->assertJsonPath('flow_choices.native_write_authorized', false)
        ->assertHeader('Cache-Control', 'no-store, private');
});

it('saves only owner-selected existing native resource IDs; refuses inline policies', function (): void {
    $id = '00000000-0000-4000-8000-000000000001';
    $identity = Mockery::mock(IdentityGateway::class);
    $identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $id, true));
    $this->app->instance(IdentityGateway::class, $identity);
    $planning = Mockery::mock(PlanningGateway::class);
    $this->app->instance(PlanningGateway::class, $planning);
    $data = [
        'command_key' => $id, 'revision' => 0,
        'context_sha256' => str_repeat('a', 64),
        'omissions' => [], 'selections' => [[
            'source_flow_id' => str_repeat('b', 64),
            'rule_native_ref' => 'native-rule-123', 'route_native_ref' => 'native-route-456',
        ]],
    ];
    $base = '/tenants/'.$id.'/applications/'.$id.'/environments/'.$id.'/planning/migration-support/'.$id;
    $planning->shouldReceive('call')->once()->with(
        str_repeat('a', 64), $id, $id, $id, 'POST', 'migration-flow-selections',
        [$id], ['site_id' => $id, 'revision' => 0, 'context_sha256' => str_repeat('a', 64),
            'selections' => $data['selections'], 'omissions' => []], $id
    )->andReturn(['status' => 'held', 'revision' => 1, 'holds' => ['isolation_missing'],
        'native_write_authorized' => false]);
    $this->withSession(['identity.token' => str_repeat('a', 64)])
        ->from($base)->post($base.'/flow-selections', $data)->assertRedirect($base);
    $data['selections'][0]['new_firewall_rule'] = 'allow all';
    $this->from($base)->post($base.'/flow-selections', $data)
        ->assertSessionHasErrors('selections.0');
});
