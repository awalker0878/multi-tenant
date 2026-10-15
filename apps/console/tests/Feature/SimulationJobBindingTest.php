<?php

declare(strict_types=1);

use App\Domain\Jobs\JobsFailure;
use App\Infrastructure\Jobs\JobsClient;
use Illuminate\Support\Facades\Http;

it('rejects schema valid simulation responses bound to a different request', function (string $method, string $tail, string $field): void {
    $id = '00000000-0000-4000-8000-000000000001';
    $other = '00000000-0000-4000-8000-000000000002';
    $scope = ['site_id' => $id, 'environment' => $id, 'resource_id' => $id];
    $key = '00000000-0000-4000-8000-000000000003';
    $command = $tail === 'commands';
    $tail = $tail === 'admit' ? 'jobs' : 'jobs/'.$id.($command ? '/commands' : '');
    $body = $command ? ['action' => 'reconcile', 'expected_revision' => 1]
        : ($method === 'POST' ? ['plan_id' => $id, 'plan_digest' => str_repeat('a', 64), 'approval_id' => $id] : []);
    $value = $command ? ['command_id' => $key, 'job_id' => $id, 'action' => 'reconcile', 'accepted' => true, 'effect_undone' => false]
        : ['id' => $id, 'tenant_id' => $id, 'actor_id' => $id, 'requested_by' => $id, 'plan_id' => $id, 'approval_id' => $id,
            'source_revision' => str_repeat('a', 40), 'scope' => ['tenant_id' => $id, ...$scope, 'endpoint_id' => $id, 'native_scope' => 'isolated'],
            'plan_digest' => str_repeat('a', 64), 'workflow_id' => 'simulation', 'workflow_run_id' => null,
            'state' => 'admitted', 'reason' => null, 'revision' => 1, 'observed_at' => 100, 'updated_at' => 100,
            'simulation' => true, 'evidence_level' => 'E2', 'native_write_authorized' => false,
            'cancel_requested' => false, 'pause_requested' => false, 'stop_requested' => false, 'resources_retained' => true,
            'evidence' => null, 'recovery_mode' => 'pre_target_write_reconciliation', 'operations' => [], 'events' => []];
    $poisoned = $value;
    $poisoned[$field] = $field === 'action' ? 'stop' : ($field === 'plan_digest' ? str_repeat('b', 64) : $other);
    $gov = tempnam(sys_get_temp_dir(), 'sim-gov-');
    $secret = tempnam(sys_get_temp_dir(), 'sim-lifecycle-');
    file_put_contents($gov, str_repeat('b', 64));
    file_put_contents($secret, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $gov,
        'jobs.url' => 'https://lifecycle.example.test', 'jobs.credential_file' => $secret, 'jobs.ca_file' => $secret]);
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'lifecycle', 'authority_use' => 'request_bound'], 201),
        'lifecycle.example.test/*' => Http::sequence()->push($value, $method === 'POST' ? 202 : 200)->push($poisoned, $method === 'POST' ? 202 : 200)]);
    try {
        $client = app(JobsClient::class);
        expect($client->call(str_repeat('a', 64), $id, $scope, $method, $tail, $body, $key))->toMatchArray($value);
        try {
            $client->call(str_repeat('a', 64), $id, $scope, $method, $tail, $body, $key);
            test()->fail('A schema-valid response from a different request was accepted');
        } catch (JobsFailure $failure) {
            expect($failure->status)->toBe(403)->and($failure->reason)->toBe('scope_mismatch');
        }
    } finally {
        unlink($gov);
        unlink($secret);
    }
})->with([
    ['GET', 'read', 'id'],
    ['POST', 'admit', 'plan_id'],
    ['POST', 'admit', 'plan_digest'],
    ['POST', 'admit', 'approval_id'],
    ['POST', 'commands', 'job_id'],
    ['POST', 'commands', 'command_id'],
    ['POST', 'commands', 'action'],
]);
