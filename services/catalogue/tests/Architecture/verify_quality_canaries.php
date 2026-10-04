<?php

declare(strict_types=1);

use Symfony\Component\Process\Process;

require dirname(__DIR__, 2).'/vendor/autoload.php';

$root = dirname(__DIR__, 2);
$created = [];
$temporary = tempnam(sys_get_temp_dir(), 'catalogue-boundaries-');

if ($temporary === false) {
    throw new RuntimeException('Cannot allocate a private report file.');
}

/** @param list<string> $arguments */
function runTool(array $arguments, string $root): Process
{
    $process = new Process($arguments, $root);
    $process->setTimeout(120);
    $process->run();

    return $process;
}

function requireSuccess(Process $process, string $label): void
{
    if (! $process->isSuccessful()) {
        throw new RuntimeException($label."\n".$process->getOutput().$process->getErrorOutput());
    }
}

/** @return array{Process, array<string, mixed>} */
function analyse(string $root, string $report): array
{
    if (is_file($report)) {
        unlink($report);
    }

    $process = runTool([
        PHP_BINARY, 'vendor/bin/deptrac', 'analyse', '--no-cache', '--no-ansi',
        '--fail-on-uncovered', '--formatter=json', '--output='.$report,
    ], $root);

    if (! is_file($report)) {
        throw new RuntimeException('Deptrac produced no structured report: '.$process->getErrorOutput());
    }

    return [$process, json_decode(file_get_contents($report), true, 512, JSON_THROW_ON_ERROR)];
}

/** @param list<string> $created */
function writeCanary(string $root, string $relative, string $body, array &$created): string
{
    $path = $root.'/'.$relative;
    if (file_exists($path)) {
        throw new RuntimeException('Refusing to overwrite an existing canary: '.$path);
    }
    if (! is_dir(dirname($path)) && ! mkdir(dirname($path), 0755, true)) {
        throw new RuntimeException('Cannot create private canary directory.');
    }
    if (file_put_contents($path, $body) === false) {
        throw new RuntimeException('Cannot write canary.');
    }
    $created[] = $path;

    return $path;
}

function canarySource(string $namespace, string $target): string
{
    return "<?php\n\ndeclare(strict_types=1);\n\nnamespace ".$namespace.";\n\nfinal class BoundaryCanary\n{\n    public function __construct(public \\".$target." \$dependency) {}\n}\n";
}

try {
    [$baseline] = analyse($root, $temporary);
    requireSuccess($baseline, 'Unmodified service boundary baseline failed.');

    // Temporary parser controls exercise the approved convention, not business behavior.
    $positives = [
        ['Domain', 'Illuminate\\Database\\Eloquent\\Model'],
        ['Application', 'Illuminate\\Support\\Facades\\DB'],
        ['Application', 'Illuminate\\Support\\Facades\\Gate'],
        ['Infrastructure', 'Product\\Contracts\\BoundaryFixture'],
    ];
    foreach ($positives as [$origin, $target]) {
        $path = writeCanary(
            $root,
            'app/'.$origin.'/Quality/BoundaryCanary.php',
            canarySource('App\\'.$origin.'\\Quality', $target),
            $created,
        );
        [$positive] = analyse($root, $temporary);
        requireSuccess($positive, 'Allowed convention control rejected: '.$origin.' -> '.$target);
        unlink($path);
        echo 'PASS allowed boundary: '.$origin.' -> '.$target.PHP_EOL;
    }

    $negatives = [
        ['Domain', 'Application', 'App\\Application\\Quality\\BoundaryTarget'],
        ['Domain', 'Infrastructure', 'App\\Infrastructure\\Quality\\BoundaryTarget'],
        ['Domain', 'Delivery', 'App\\Http\\BoundaryTarget'],
        ['Application', 'Infrastructure', 'App\\Infrastructure\\Quality\\BoundaryTarget'],
        ['Application', 'Delivery', 'App\\Http\\BoundaryTarget'],
        ['Domain', 'Transport', 'Illuminate\\Http\\Request'],
        ['Application', 'Transport', 'Illuminate\\Support\\Facades\\Http'],
        ['Application', 'PublishedContracts', 'Product\\Contracts\\BoundaryFixture'],
        ['Application', 'ForeignPrivate', 'Product\\Services\\Foreign\\PrivateModel'],
    ];
    foreach ($negatives as [$origin, $destination, $target]) {
        $name = 'App\\'.$origin.'\\Quality\\BoundaryCanary';
        $path = writeCanary(
            $root,
            'app/'.$origin.'/Quality/BoundaryCanary.php',
            canarySource('App\\'.$origin.'\\Quality', $target),
            $created,
        );
        [$negative, $report] = analyse($root, $temporary);
        $expected = $name.' must not depend on '.$target.' ('.$origin.' on '.$destination.')';
        $messages = [];
        foreach ($report['files'] as $file) {
            foreach ($file['messages'] as $message) {
                $messages[] = $message['message'];
            }
        }
        $summary = $report['Report'];
        if ($negative->getExitCode() !== 1 || $messages === []
            || array_filter($messages, fn (string $message): bool => $message !== $expected) !== []
            || $summary['Violations'] !== count($messages)) {
            throw new RuntimeException('Wrong boundary failure: '.json_encode($report, JSON_THROW_ON_ERROR));
        }
        foreach (['Skipped violations', 'Uncovered', 'Warnings', 'Errors'] as $key) {
            if (($summary[$key] ?? 0) !== 0) {
                throw new RuntimeException('Unexpected analyzer failure: '.$key);
            }
        }
        unlink($path);
        echo 'PASS forbidden boundary: '.$origin.' -> '.$destination.PHP_EOL;
    }

    [$restored] = analyse($root, $temporary);
    requireSuccess($restored, 'Restored service boundary baseline failed.');
    echo 'PASS: 4 allowed convention controls and 9 forbidden dependencies; source restored.'.PHP_EOL;
} finally {
    foreach ($created as $path) {
        if (is_file($path)) {
            unlink($path);
        }
    }
    if (is_file($temporary)) {
        unlink($temporary);
    }
}
