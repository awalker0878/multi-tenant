<?php

declare(strict_types=1);

use App\Infrastructure\Foundation\MountedSecret;
use App\Infrastructure\Planning\PlanningInputAuthority;
use Illuminate\Support\Facades\Http;
use Symfony\Component\HttpKernel\Exception\HttpException;

it('requires typed planning scope values while accepting reordered object keys', function (string $field): void {
    Http::preventStrayRequests();
    $incoming = tempnam(sys_get_temp_dir(), 'catalogue-incoming-');
    $outgoing = tempnam(sys_get_temp_dir(), 'catalogue-outgoing-');
    file_put_contents($incoming, str_repeat('a', 64));
    file_put_contents($outgoing, str_repeat('b', 64));
    config(['planning.credential_file' => $incoming, 'planning.governance_credential_file' => $outgoing,
        'planning.governance_url' => 'https://governance.example.test', 'planning.ca_file' => $outgoing]);
    $id = '10000000-0000-4000-8000-000000000001';
    $scope = ['site_id' => $id, 'environment' => $id, 'resource_id' => $id];
    $headers = ['authorization' => ['Bearer '.str_repeat('a', 64)], 'x-actor-delegation' => [str_repeat('c', 64)], 'x-planning-action' => ['plan.read']];
    $response = ['allowed' => true, 'audience' => 'planning', 'source_owner' => 'catalogue', 'source_use' => 'planning_read_only',
        'tenant_id' => $id, 'action' => 'plan.read', 'scope' => array_reverse($scope, true), 'authority_use' => 'request_bound',
        'expires_at' => now()->addSeconds(60)->toIso8601String(), 'evaluated_at' => now()->toIso8601String()];
    try {
        $invalid = $response;
        $invalid['scope'][$field] = true;
        Http::fakeSequence('governance.example.test/*')->push($response)->push($invalid);
        $authority = new PlanningInputAuthority(new MountedSecret);
        expect($authority->check($headers, $id, $scope)['allowed'])->toBeTrue();
        expect(fn () => $authority->check($headers, $id, $scope))->toThrow(HttpException::class, 'source_authority_unavailable');
    } finally {
        unlink($incoming);
        unlink($outgoing);
    }
})->with(['site_id', 'environment', 'resource_id']);
