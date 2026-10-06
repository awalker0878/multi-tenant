<?php

declare(strict_types=1);

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Planning\Contracts\ApprovalGateway;
use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Planning\PlanningFailure;
use App\Infrastructure\Planning\PlanningClient;
use Illuminate\Support\Facades\Http;

beforeEach(function (): void {
    $this->id = '00000000-0000-4000-8000-000000000001';
    $this->base = '/tenants/'.$this->id.'/applications/'.$this->id.'/environments/'.$this->id.'/planning';
    $identity = Mockery::mock(IdentityGateway::class);
    $identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $this->id, true));
    $this->app->instance(IdentityGateway::class, $identity);
    $this->planning = Mockery::mock(PlanningGateway::class);
    $this->approvals = Mockery::mock(ApprovalGateway::class);
    $this->app->instance(PlanningGateway::class, $this->planning);
    $this->app->instance(ApprovalGateway::class, $this->approvals);
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
});

it('requires a fresh matching plan digest before requesting approval', function (bool $current, string $digest): void {
    $this->planning->shouldReceive('call')->once()->andReturn(['id' => $this->id, 'validity' => ['current' => $current], 'binding' => ['digest' => $digest]]);
    $this->approvals->shouldNotReceive('request');
    $this->from($this->base)->post($this->base.'/commands', ['operation' => 'approval', 'command_key' => $this->id, 'sites' => [$this->id], 'body' => ['plan_id' => $this->id, 'plan_digest' => str_repeat('b', 64)]])
        ->assertRedirect($this->base)->assertSessionHasErrors(['planning_status' => '409']);
})->with([[false, str_repeat('b', 64)], [true, str_repeat('c', 64)]]);

it('hands the exact fresh immutable revision and expiry to Governance', function (): void {
    $expiry = time() + 600;
    $this->planning->shouldReceive('call')->once()->andReturn(['id' => $this->id, 'validity' => ['current' => true], 'binding' => ['digest' => str_repeat('b', 64), 'revision' => 1, 'valid_until' => $expiry]]);
    $this->approvals->shouldReceive('request')->once()->with(str_repeat('a', 64), $this->id, ['plan_id' => $this->id, 'plan_revision' => 1, 'plan_digest' => str_repeat('b', 64), 'expires_at' => gmdate('c', $expiry)], $this->id)->andReturn(['id' => $this->id]);
    $this->post($this->base.'/commands', ['operation' => 'approval', 'command_key' => $this->id, 'sites' => [$this->id], 'body' => ['plan_id' => $this->id, 'plan_digest' => str_repeat('b', 64)]])
        ->assertRedirect($this->base.'/plans/'.$this->id.'?sites='.$this->id)->assertSessionHas('planning_notice');
});

it('retains the same command body and identity after an uncertain result', function (): void {
    $body = ['assessment_id' => $this->id, 'candidate' => 0, 'request' => ['lane' => 'operational']];
    $this->planning->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, $this->id, $this->id, 'POST', 'plans', [$this->id], $body, $this->id)->andThrow(new PlanningFailure(503));
    $this->from($this->base)->post($this->base.'/commands', ['operation' => 'plans', 'command_key' => $this->id, 'sites' => [$this->id], 'body' => $body])
        ->assertRedirect($this->base)->assertSessionHasErrors(['planning_status' => '503'])->assertSessionHasInput('command_key', $this->id)->assertSessionHasInput('body', $body);
});

it('removes revoked planning access and uses real CSRF protection', function (): void {
    $this->planning->shouldReceive('call')->once()->andThrow(new PlanningFailure(403));
    $this->get($this->base.'/plans/'.$this->id.'/status?sites='.$this->id)->assertRedirect('/account');
    $this->app['env'] = 'csrf-check';
    $this->post($this->base.'/commands')->assertStatus(419);
});

it('binds request delegation and rejects extra response fields', function (): void {
    $gov = tempnam(sys_get_temp_dir(), 'p05-gov-');
    $plan = tempnam(sys_get_temp_dir(), 'p05-plan-');
    file_put_contents($gov, str_repeat('b', 64));
    file_put_contents($plan, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $gov, 'planning.url' => 'https://planning.example.test', 'planning.credential_file' => $plan, 'planning.ca_file' => $plan]);
    $validity = ['current' => false, 'holds' => ['plan_or_facts_expired'], 'evaluated_at' => time(), 'approval_digest' => str_repeat('e', 64), 'native_write_authorized' => false];
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'planning', 'authority_use' => 'request_bound'], 201), 'planning.example.test/*' => Http::sequence()->push($validity)->push($validity + ['secret' => 'unexpected'])]);
    try {
        $client = app(PlanningClient::class);
        expect($client->call(str_repeat('a', 64), $this->id, $this->id, $this->id, 'POST', 'plans/'.$this->id.'/validity', [$this->id]))->toBe($validity);
        Http::assertSent(fn ($r) => str_contains($r->url(), 'planning.example.test') && $r->hasHeader('Authorization', 'Bearer '.str_repeat('c', 64)) && $r->hasHeader('X-Planning-Delegations', $this->id.':'.str_repeat('d', 64)) && ! $r->hasHeader('X-Console-Session'));
        expect(fn () => $client->call(str_repeat('a', 64), $this->id, $this->id, $this->id, 'POST', 'plans/'.$this->id.'/validity', [$this->id]))->toThrow(PlanningFailure::class);
    } finally {
        unlink($gov);
        unlink($plan);
    }
});
