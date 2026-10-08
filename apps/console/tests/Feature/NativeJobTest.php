<?php

declare(strict_types=1);

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Jobs\Contracts\JobsGateway;
use App\Domain\Jobs\JobsFailure;
use App\Infrastructure\Jobs\JobsClient;
use Illuminate\Support\Facades\Http;

beforeEach(function (): void {
    $this->id = '00000000-0000-4000-8000-000000000001';
    $this->scope = ['site_id' => $this->id, 'environment' => $this->id, 'resource_id' => $this->id];
    $this->base = '/tenants/'.$this->id.'/sites/'.$this->id.'/applications/'.$this->id.'/environments/'.$this->id.'/native-jobs/'.$this->id;
    $identity = Mockery::mock(IdentityGateway::class);
    $identity->shouldReceive('current')->andReturn(new ConsoleActor(false, $this->id, true));
    $this->app->instance(IdentityGateway::class, $identity);
    $this->jobs = Mockery::mock(JobsGateway::class);
    $this->app->instance(JobsGateway::class, $this->jobs);
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
});

it('binds native controls to the route scope and forwards only the expected revision', function (string $action): void {
    $this->jobs->shouldReceive('call')->once()->with(str_repeat('a', 64), $this->id, $this->scope,
        'POST', 'native-jobs/'.$this->id.'/'.$action, ['expected_revision' => 3])->andReturn(['revision' => 4]);
    $this->postJson($this->base.'/commands', ['action' => $action, 'expected_revision' => 3, 'scope' => ['tenant_id' => 'forged'], 'retry_authorized' => true])
        ->assertStatus(202)->assertJsonPath('revision', 4)->assertHeader('Cache-Control', 'no-store, private');
})->with(['stop', 'continue-transfer']);

it('retains holds and real CSRF protection instead of claiming a successful native effect', function (): void {
    $this->jobs->shouldReceive('call')->once()->andThrow(new JobsFailure(423, 'native_attempt_requires_reconciliation'));
    $this->postJson($this->base.'/commands', ['action' => 'continue-transfer', 'expected_revision' => 3])
        ->assertStatus(423)->assertExactJson(['error' => 'native_attempt_requires_reconciliation']);
    $this->app['env'] = 'csrf-check';
    $this->post($this->base.'/commands', ['action' => 'stop', 'expected_revision' => 3])->assertStatus(419);
});

it('rejects arbitrary native actions before forwarding', function (): void {
    $this->jobs->shouldNotReceive('call');
    $this->postJson($this->base.'/commands', ['action' => 'activate', 'expected_revision' => 3])->assertUnprocessable();
});

it('validates native observations and refuses cross-scope job responses', function (): void {
    $gov = tempnam(sys_get_temp_dir(), 'native-gov-');
    $secret = tempnam(sys_get_temp_dir(), 'native-lifecycle-');
    file_put_contents($gov, str_repeat('b', 64));
    file_put_contents($secret, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $gov,
        'jobs.url' => 'https://lifecycle.example.test', 'jobs.credential_file' => $secret, 'jobs.ca_file' => $secret]);
    $job = ['job_id' => $this->id, 'tenant_id' => $this->id, 'state' => 'held', 'revision' => 3,
        'stopped' => false, 'hold_reason' => 'native_outcome_unknown', 'transfer_continuation_candidate' => true,
        'plan_sha256' => str_repeat('a', 64), 'scope' => ['tenant_id' => $this->id, ...$this->scope, 'project_id' => $this->id],
        'operations' => [], 'retry_authorized' => false, 'native_qualification' => 'not_established',
        'measurements' => ['observed_at' => 100, 'started_at' => 90, 'total_stages' => 8, 'completed_stages' => 0, 'operations' => [], 'transfer' => null]];
    $foreign = $job;
    $foreign['scope']['site_id'] = '00000000-0000-4000-8000-000000000002';
    $differentJob = $job;
    $differentJob['job_id'] = '00000000-0000-4000-8000-000000000002';
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'lifecycle', 'authority_use' => 'request_bound'], 201),
        'lifecycle.example.test/*' => Http::sequence()->push($job)->push($foreign)->push($differentJob)->push($job + ['untrusted' => true])]);
    try {
        $client = app(JobsClient::class);
        expect($client->call(str_repeat('a', 64), $this->id, $this->scope, 'GET', 'native-jobs/'.$this->id)['measurements']['completed_stages'])->toBe(0);
        Http::assertSent(fn ($request) => str_contains($request->url(), 'lifecycle.example.test')
            && $request->hasHeader('X-Actor-Delegation', str_repeat('d', 64)) && ! $request->hasHeader('X-Console-Session'));
        expect(fn () => $client->call(str_repeat('a', 64), $this->id, $this->scope, 'GET', 'native-jobs/'.$this->id))->toThrow(JobsFailure::class);
        expect(fn () => $client->call(str_repeat('a', 64), $this->id, $this->scope, 'GET', 'native-jobs/'.$this->id))->toThrow(JobsFailure::class);
        expect(fn () => $client->call(str_repeat('a', 64), $this->id, $this->scope, 'GET', 'native-jobs/'.$this->id))->toThrow(JobsFailure::class);
    } finally {
        unlink($gov);
        unlink($secret);
    }
});
