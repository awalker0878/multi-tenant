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
