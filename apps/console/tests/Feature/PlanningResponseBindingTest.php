<?php

declare(strict_types=1);

use App\Domain\Planning\PlanningFailure;
use App\Infrastructure\Planning\PlanningClient;
use Illuminate\Support\Facades\Http;

it('rejects a schema valid Planning response for a different record or scope', function (string $field): void {
    $fixture = json_decode(file_get_contents(base_path('../../contracts/fixtures/planning/synthetic-plan-v1.1.json')), true, 512, JSON_THROW_ON_ERROR);
    $binding = $fixture['binding'];
    $scope = $fixture['content']['scope'];
    $candidate = ['site_id' => $scope['site_id'], 'endpoint_id' => $scope['endpoint_id'], 'generation_id' => '10000000-0000-4000-8000-000000000008'];
    $value = ['id' => $binding['plan_id'], 'assessment_id' => '10000000-0000-4000-8000-000000000009',
        'content' => $fixture['content'], 'binding' => $binding, 'candidates' => [$candidate], 'candidate' => 0,
        'application_id' => $binding['resource_id'], 'environment' => $binding['environment'], 'tenant_id' => $binding['tenant_id'],
        'validity' => ['current' => true, 'holds' => [], 'evaluated_at' => time(), 'approval_digest' => $binding['digest'], 'native_write_authorized' => false]];
    $poisoned = $value;
    data_set($poisoned, $field, '20000000-0000-4000-8000-000000000001');
    $gov = tempnam(sys_get_temp_dir(), 'plan-binding-gov-');
    $secret = tempnam(sys_get_temp_dir(), 'plan-binding-secret-');
    file_put_contents($gov, str_repeat('b', 64));
    file_put_contents($secret, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $gov,
        'planning.url' => 'https://planning.example.test', 'planning.credential_file' => $secret, 'planning.ca_file' => $secret]);
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'planning', 'authority_use' => 'request_bound'], 201),
        'planning.example.test/*' => Http::sequence()->push($value)->push($poisoned)]);
    try {
        $invoke = fn () => app(PlanningClient::class)->call(str_repeat('a', 64), $binding['tenant_id'], $binding['resource_id'], $binding['environment'], 'GET', 'plans/'.$binding['plan_id'], [$binding['site_id']]);
        expect($invoke())->toBe($value);
        try {
            $invoke();
            test()->fail('Planning accepted a response for another record or scope');
        } catch (PlanningFailure $failure) {
            expect($failure->status)->toBe(403)->and($failure->reason)->toBe('scope_mismatch');
        }
    } finally {
        unlink($gov);
        unlink($secret);
    }
})->with(['id', 'tenant_id', 'application_id', 'environment', 'binding.plan_id', 'binding.tenant_id', 'binding.resource_id', 'binding.environment', 'binding.site_id', 'content.scope.tenant_id', 'content.scope.resource_id', 'content.scope.environment', 'content.scope.site_id']);

it('requires the exact installed migration operation status', function (): void {
    $id = '00000000-0000-4000-8000-000000000001';
    $value = ['revision' => 1, 'status' => 'held', 'holds' => ['review_required'], 'native_write_authorized' => false];
    $gov = tempnam(sys_get_temp_dir(), 'migration-status-gov-');
    $secret = tempnam(sys_get_temp_dir(), 'migration-status-secret-');
    file_put_contents($gov, str_repeat('b', 64));
    file_put_contents($secret, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $gov,
        'planning.url' => 'https://planning.example.test', 'planning.credential_file' => $secret, 'planning.ca_file' => $secret]);
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'planning', 'authority_use' => 'request_bound'], 201),
        'planning.example.test/*' => Http::sequence()->push($value, 200)->push($value, 201)]);
    try {
        $invoke = fn () => app(PlanningClient::class)->call(str_repeat('a', 64), $id, $id, $id, 'POST', 'migration-flow-selections', [$id], [], $id);
        expect($invoke())->toBe($value);
        try {
            $invoke();
            test()->fail('Planning accepted another operation success status');
        } catch (PlanningFailure $failure) {
            expect($failure->status)->toBe(503);
        }
    } finally {
        unlink($gov);
        unlink($secret);
    }
});

it('keeps the stored record digest separate from the approval binding digest', function (string $tail): void {
    $fixture = json_decode(file_get_contents(base_path('../../contracts/fixtures/planning/synthetic-plan-v1.1.json')), true, 512, JSON_THROW_ON_ERROR);
    $binding = $fixture['binding'];
    $value = ['id' => $binding['plan_id'], 'kind' => 'plan', 'digest' => str_repeat('a', 64), 'binding' => $binding, 'native_write_authorized' => false];
    $gov = tempnam(sys_get_temp_dir(), 'plan-receipt-gov-');
    $secret = tempnam(sys_get_temp_dir(), 'plan-receipt-secret-');
    file_put_contents($gov, str_repeat('b', 64));
    file_put_contents($secret, str_repeat('c', 64));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $gov,
        'planning.url' => 'https://planning.example.test', 'planning.credential_file' => $secret, 'planning.ca_file' => $secret]);
    Http::preventStrayRequests();
    Http::fake(['governance.example.test/*' => Http::response(['delegation_token' => str_repeat('d', 64), 'audience' => 'planning', 'authority_use' => 'request_bound'], 201),
        'planning.example.test/*' => Http::response($value, 201)]);
    try {
        expect(app(PlanningClient::class)->call(str_repeat('a', 64), $binding['tenant_id'], $binding['resource_id'], $binding['environment'], 'POST', $tail, [$binding['site_id']], [], $binding['plan_id']))->toBe($value);
    } finally {
        unlink($gov);
        unlink($secret);
    }
})->with(['plans', 'migration-plans']);
