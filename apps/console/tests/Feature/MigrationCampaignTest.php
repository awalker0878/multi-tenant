<?php

declare(strict_types=1);

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Jobs\Contracts\JobsGateway;
use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Jobs\JobsFailure;
use App\Infrastructure\Jobs\JobsClient;
use Illuminate\Support\Facades\Http;

beforeEach(function (): void {
    $this->id = '00000000-0000-4000-8000-000000000001';
    $this->scope = ['site_id' => $this->id, 'environment' => $this->id, 'resource_id' => $this->id];
    $this->base = '/tenants/'.$this->id.'/sites/'.$this->id.'/applications/'.$this->id.'/environments/'.$this->id.'/migration-campaigns';
    $identity = Mockery::mock(IdentityGateway::class);
    $identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $this->id, true));
    $this->app->instance(IdentityGateway::class, $identity);
    $this->jobs = Mockery::mock(JobsGateway::class);
    $this->app->instance(JobsGateway::class, $this->jobs);
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
});

it('keeps campaign creation inside the route scope and preserves the command key', function (): void {
    $settings = ['name' => 'Wave one'];
    $members = [['id' => $this->id]];
    $this->jobs->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, $this->scope, 'POST', 'migration-campaigns', ['scope' => $this->scope, 'settings' => $settings, 'members' => $members], $this->id)->andReturn(['id' => $this->id, 'state' => 'draft']);
    $this->postJson($this->base, ['command_key' => $this->id, 'settings' => $settings, 'members' => $members, 'scope' => ['tenant_id' => 'another-tenant']])->assertStatus(202)->assertJsonPath('state', 'draft')->assertHeader('Cache-Control', 'no-store, private');
});

it('reports uncertain commands without replacing their identity or claiming completion', function (): void {
    $this->jobs->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, $this->scope, 'POST', 'migration-campaigns/'.$this->id.'/commands', ['action' => 'pause', 'expected_revision' => 3], $this->id)->andThrow(new JobsFailure(503, 'campaign_unavailable'));
    $this->postJson($this->base.'/'.$this->id.'/commands', ['command_key' => $this->id, 'action' => 'pause', 'expected_revision' => 3])->assertStatus(503)->assertExactJson(['error' => 'campaign_unavailable']);
});

it('does not convert a migration preparation into a schedulable native plan', function (): void {
    $planning = Mockery::mock(PlanningGateway::class);
    $planning->shouldReceive('call')->once()->andReturn(['validity' => ['current' => true], 'content' => ['action' => 'application.migrate', 'execution_ready' => false]]);
    $this->app->instance(PlanningGateway::class, $planning);
    $this->getJson($this->base.'/plans/'.$this->id)->assertStatus(423)->assertJsonPath('error', 'complete_current_migration_plan_required');
});

it('clears revoked access and retains real CSRF protection for campaign controls', function (): void {
    $this->jobs->shouldReceive('call')->once()->andThrow(new JobsFailure(403, 'actor_revoked'));
    $this->getJson($this->base.'/status')->assertStatus(403);
    $this->app['env'] = 'csrf-check';
    $this->post($this->base.'/'.$this->id.'/commands')->assertStatus(419);
});

it('validates campaign responses and sends only current scoped workload delegation', function (): void {
    $gov = tempnam(sys_get_temp_dir(), 'campaign-gov-');
    $secret = tempnam(sys_get_temp_dir(), 'campaign-lifecycle-');
    file_put_contents($gov, str_repeat('b', 64));
    file_put_contents($secret, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $gov, 'jobs.url' => 'https://lifecycle.example.test', 'jobs.credential_file' => $secret, 'jobs.ca_file' => $secret]);
    $list = ['tenant_id' => $this->id, 'scope' => $this->scope, 'items' => [], 'limit_reached' => false];
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'lifecycle', 'authority_use' => 'request_bound'], 201), 'lifecycle.example.test/*' => Http::sequence()->push($list)->push($list + ['unexpected' => true])]);
    try {
        $client = app(JobsClient::class);
        expect($client->call(str_repeat('a', 64), $this->id, $this->scope, 'GET', 'migration-campaigns')['items'])->toBe([]);
        Http::assertSent(fn ($r) => str_contains($r->url(), 'lifecycle.example.test') && str_contains($r->url(), 'site_id=') && $r->hasHeader('Authorization', 'Bearer '.str_repeat('c', 64)) && $r->hasHeader('X-Actor-Delegation', str_repeat('d', 64)) && ! $r->hasHeader('X-Console-Session'));
        expect(fn () => $client->call(str_repeat('a', 64), $this->id, $this->scope, 'GET', 'migration-campaigns'))->toThrow(JobsFailure::class);
    } finally {
        unlink($gov);
        unlink($secret);
    }
});
