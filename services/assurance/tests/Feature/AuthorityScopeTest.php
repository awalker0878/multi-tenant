<?php

declare(strict_types=1);

use App\Infrastructure\Evidence\EvidenceOwners;
use App\Infrastructure\Foundation\MountedSecret;
use App\Infrastructure\Planning\PlanningInputAuthority;
use Illuminate\Support\Facades\Http;
use Symfony\Component\HttpKernel\Exception\HttpException;

it('requires typed authority scope values and accepts reordered keys', function (string $caller, string $field): void {
    $incoming = tempnam(sys_get_temp_dir(), 'assurance-incoming-');
    $outgoing = tempnam(sys_get_temp_dir(), 'assurance-outgoing-');
    file_put_contents($incoming, str_repeat('a', 64));
    file_put_contents($outgoing, str_repeat('b', 64));
    config([
        'planning.credential_file' => $incoming, 'planning.governance_credential_file' => $outgoing,
        'planning.governance_url' => 'https://governance.example', 'planning.ca_file' => $outgoing,
        'evidence.console_file' => $incoming, 'evidence.governance_file' => $outgoing,
        'evidence.governance_url' => 'https://governance.example', 'evidence.governance_ca' => $outgoing,
    ]);
    $id = '10000000-0000-4000-8000-000000000001';
    $scope = ['site_id' => $id, 'environment' => $id, 'resource_id' => $id];
    $headers = ['authorization' => ['Bearer '.str_repeat('a', 64)], 'x-actor-delegation' => [str_repeat('c', 64)], 'x-planning-action' => ['plan.read']];
    $response = ['allowed' => true, 'audience' => $caller === 'planning' ? 'planning' : 'assurance',
        'source_owner' => 'assurance', 'source_use' => 'planning_read_only', 'tenant_id' => $id,
        'action' => $caller === 'planning' ? 'plan.read' : 'evidence.read', 'scope' => array_reverse($scope, true),
        'authority_use' => 'request_bound', 'expires_at' => now()->addSeconds(60)->toIso8601String(),
        'evaluated_at' => now()->toIso8601String()];
    $check = static function () use ($caller, $headers, $id, $scope): array {
        $secrets = new MountedSecret;

        return $caller === 'planning'
            ? (new PlanningInputAuthority($secrets))->check($headers, $id, $scope)
            : (new EvidenceOwners($secrets))->reader($headers, $id, $scope, 'evidence.read');
    };
    try {
        $invalid = $response;
        $invalid['scope'][$field] = true;
        Http::fakeSequence('governance.example/*')->push($response)->push($invalid);
        expect($check()['allowed'])->toBeTrue();
        expect($check)->toThrow(HttpException::class);
    } finally {
        unlink($incoming);
        unlink($outgoing);
    }
})->with(['planning', 'evidence'])->with(['site_id', 'environment', 'resource_id']);
