<?php

declare(strict_types=1);

use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Planning\PlanningFailure;
use App\Infrastructure\Planning\PlanningClient;
use Illuminate\Contracts\Console\Kernel;

if (getenv('GITHUB_ACTIONS') !== 'true' || getenv('P05_TEST_POSTGRES') !== '1') {
    exit(2);
}
$root = dirname(__DIR__, 2);
require $root.'/apps/console/vendor/autoload.php';
$app = require $root.'/apps/console/bootstrap/app.php';
$app->make(Kernel::class)->bootstrap();
$input = json_decode(file_get_contents($argv[1]), true, 512, JSON_THROW_ON_ERROR);
$client = app(PlanningGateway::class);
if (! $client instanceof PlanningClient) {
    throw new RuntimeException('Qualification requires the shipped Planning consumer');
}
$canonical = 'contracts/openapi/planning-v1.2.json';
$installed = 'apps/console/resources/contracts/planning-v1.2.json';
$loader = 'apps/console/app/Infrastructure/Planning/PlanningClient.php';
if (file_get_contents($root.'/'.$canonical) !== file_get_contents($root.'/'.$installed)) {
    throw new RuntimeException('Console installed Planning release differs');
}
$proofs = [];
try {
    foreach ($input['calls'] as $call) {
        $invoke = fn (): array => $client->call($input['session'], $input['tenant'], $input['application'], $input['environment'],
            $call['method'], $call['tail'], $call['sites'], $call['body'], $call['key']);
        // The shipped client obtains real current Governance delegation, then
        // consumes the live Planning process over its configured verified TLS.
        $value = $invoke();
        foreach ($call['faults'] as $field) {
            file_put_contents($input['fault_file'], json_encode(['mode' => 'poison_response', 'method' => $call['method'],
                'path' => $input['base'].'/'.$call['tail'], 'field' => $field], JSON_THROW_ON_ERROR));
            chmod($input['fault_file'], 0600);
            $denied = false;
            try {
                $invoke();
            } catch (PlanningFailure $failure) {
                $denied = in_array($failure->status, [403, 503], true);
            }
            if (! $denied || file_exists($input['fault_file'])) {
                throw new RuntimeException('Console accepted an unbound Planning response: '.$field);
            }
        }
        $proofs[] = ['key' => json_encode(['planning', $call['method'], $call['path']], JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR),
            'claim' => 'consumer', 'source' => 'live-consumer', 'result' => 'PASS', 'consumer_id' => 'console',
            'release_sha256' => hash_file('sha256', $root.'/'.$canonical),
            'test' => 'scripts/p05/verify_console_consumers.php:PlanningClient',
            'consumer_loader' => $loader, 'loader_sha256' => hash_file('sha256', $root.'/'.$loader),
            'installed_copy' => $installed, 'installed_sha256' => hash_file('sha256', $root.'/'.$installed),
            'response_sha256' => hash('sha256', json_encode($value, JSON_THROW_ON_ERROR)),
            'positive_status_code' => $call['status'], 'rejected_response_substitutions' => $call['faults'],
            'revision' => getenv('GITHUB_SHA'), 'run_id' => getenv('GITHUB_RUN_ID'), 'run_attempt' => getenv('GITHUB_RUN_ATTEMPT')];
    }
    if (count($proofs) !== 6) {
        throw new RuntimeException('Incomplete Planning consumer controls');
    }
    file_put_contents($argv[2], json_encode($proofs, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)."\n");
    echo "Shipped Console PlanningClient: six live operations and response substitution controls.\n";
} finally {
    if (file_exists($input['fault_file'])) {
        unlink($input['fault_file']);
    }
}
