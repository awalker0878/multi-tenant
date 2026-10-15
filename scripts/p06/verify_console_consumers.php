<?php

declare(strict_types=1);

use App\Application\Jobs\Contracts\JobsGateway;
use App\Domain\Jobs\JobsFailure;
use App\Infrastructure\Jobs\JobsClient;

if (getenv('GITHUB_ACTIONS') !== 'true' || getenv('P03_TEST_POSTGRES') !== '1') {
    exit(2);
}
$root = dirname(__DIR__, 2);
require $root.'/apps/console/vendor/autoload.php';
$app = require $root.'/apps/console/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$input = json_decode(file_get_contents($argv[1]), true, 512, JSON_THROW_ON_ERROR);
$client = app(JobsGateway::class);
if (! $client instanceof JobsClient) {
    throw new RuntimeException('Qualification requires the shipped Console consumer');
}
$canonical = 'contracts/openapi/lifecycle-v1.json';
$installed = 'apps/console/resources/contracts/lifecycle-v1.json';
$loader = 'apps/console/app/Infrastructure/Jobs/JobsClient.php';
if (file_get_contents($root.'/'.$canonical) !== file_get_contents($root.'/'.$installed)) {
    throw new RuntimeException('Console installed release differs from the owner');
}
$proofs = [];
$negativeCount = 0;
try {
    foreach ($input['calls'] as $call) {
        $invoke = fn (): array => $client->call($input['session'], $input['tenant'], $input['scope'],
            $call['method'], $call['tail'], $call['body'], $call['key']);
        // No fake HTTP facade, fixture gateway or substituted owner response:
        // the actual client obtains current Governance delegation and calls
        // the live Lifecycle service through its configured verified TLS link.
        $value = $invoke();
        $command = str_ends_with($call['tail'], '/commands');
        if (($value[$command ? 'job_id' : 'id'] ?? null) !== $input['job_id']) {
            throw new RuntimeException('Console accepted a different owner job');
        }
        $faults = $command ? ['job_id', 'command_id', 'action'] : ($call['method'] === 'POST'
            ? ['plan_id', 'plan_digest', 'approval_id'] : ['id', 'tenant_id', 'uncontracted']);
        foreach ($faults as $field) {
            file_put_contents($input['fault_file'], json_encode(['mode' => 'poison_response', 'method' => $call['method'],
                'path' => '/v1/tenants/'.$input['tenant'].'/'.$call['tail'], 'field' => $field], JSON_THROW_ON_ERROR));
            chmod($input['fault_file'], 0600);
            $denied = false;
            try {
                $invoke();
            } catch (JobsFailure $failure) {
                $denied = in_array($failure->status, [403, 503], true);
            }
            if (! $denied || file_exists($input['fault_file'])) {
                throw new RuntimeException('Console accepted an unbound owner response: '.$field);
            }
            $negativeCount++;
        }
        $proofs[] = ['key' => json_encode(['lifecycle', $call['method'], $call['path']], JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR),
            'claim' => 'consumer', 'source' => 'live-consumer', 'result' => 'PASS', 'consumer_id' => 'console',
            'release_sha256' => hash_file('sha256', $root.'/'.$canonical),
            'test' => 'scripts/p06/verify_console_consumers.php:JobsClient',
            'consumer_loader' => $loader, 'loader_sha256' => hash_file('sha256', $root.'/'.$loader),
            'installed_copy' => $installed, 'installed_sha256' => hash_file('sha256', $root.'/'.$installed),
            'response_sha256' => hash('sha256', json_encode($value, JSON_THROW_ON_ERROR)),
            'positive_status_code' => $call['method'] === 'POST' ? 202 : 200,
            'rejected_response_substitutions' => $faults,
            'revision' => getenv('GITHUB_SHA'), 'run_id' => getenv('GITHUB_RUN_ID'),
            'run_attempt' => getenv('GITHUB_RUN_ATTEMPT')];
    }
    if (count($proofs) !== 3 || $negativeCount !== 9) {
        throw new RuntimeException('Incomplete Console qualification controls');
    }
    file_put_contents($argv[2], json_encode($proofs, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR)."\n");
    echo "Shipped Console JobsClient: 3 live consumers, 9 substituted responses rejected.\n";
} finally {
    if (file_exists($input['fault_file'])) {
        unlink($input['fault_file']);
    }
}
