<?php

declare(strict_types=1);

/**
 * Exercise every published authenticated Laravel HTTP operation without credentials.
 * Never substitute a mocked route, a schema example or a service error for a denial.
 *
 * Usage: php scripts/contracts/laravel_denials.php governance /tmp/evidence.json
 */
if ($argc !== 3 || ! in_array($argv[1], ['catalogue', 'governance', 'assurance'], true)) {
    throw new RuntimeException('Expected bounded Laravel owner and output file');
}
$root = dirname(__DIR__, 2);
$owner = $argv[1];
$registry = json_decode((string) file_get_contents($root.'/architecture/contract-consumers.json'), true, 512, JSON_THROW_ON_ERROR);
require $root.'/services/'.$owner.'/vendor/autoload.php';
$app = require $root.'/services/'.$owner.'/bootstrap/app.php';
$kernel = $app->make(\Illuminate\Contracts\Http\Kernel::class);
$uuid = '10000000-0000-4000-8000-000000000001';
$evidence = [];
$expected = 0;
$failures = [];
foreach ($registry['active_releases'] as $entry) {
    if ($entry['owner'] !== $owner || ! str_starts_with($entry['path'], 'contracts/openapi/')) {
        continue;
    }
    $canonical = $root.'/'.$entry['path'];
    $spec = json_decode((string) file_get_contents($canonical), true, 512, JSON_THROW_ON_ERROR);
    $fingerprint = hash_file('sha256', $canonical);
    foreach ($spec['paths'] as $template => $verbs) {
        foreach ($verbs as $verb => $operation) {
            if (! in_array($verb, ['get', 'post', 'put', 'patch', 'delete'], true)) {
                continue;
            }
            $security = $operation['security'] ?? ($spec['security'] ?? []);
            if ($security === [] || $security === [[]]) {
                continue;
            }
            $expected++;
            $uri = preg_replace_callback('/\{([^}]+)\}/', static function (array $match) use ($uuid): string {
                if ($match[1] === 'digest') {
                    return str_repeat('a', 64);
                }
                return $uuid;
            }, $template);
            // Intentionally no Authorization or delegated actor. All other
            // request properties are inert; product databases must not be reached.
            $request = \Illuminate\Http\Request::create(
                $uri, strtoupper($verb), [], [], [], [
                    'HTTP_ACCEPT' => 'application/json',
                    'CONTENT_TYPE' => 'application/json',
                ], '{}'
            );
            try {
                $response = $kernel->handle($request);
                $code = $response->getStatusCode();
                $kernel->terminate($request, $response);
            } catch (\Throwable $error) {
                $failures[] = $entry['path'].':'.strtoupper($verb).' '.$template.': exception '.$error::class;
                continue;
            }
            if (! in_array($code, [401, 403], true)) {
                $failures[] = $entry['path'].':'.strtoupper($verb).' '.$template.': expected 401/403, received '.$code;
                continue;
            }
            $key = json_encode([$owner, strtoupper($verb), $template], JSON_THROW_ON_ERROR);
            $evidence[] = [
                'key' => $key,
                'claim' => 'authorization',
                'source' => 'live-denial',
                'result' => 'PASS',
                'release_sha256' => $fingerprint,
                'test' => 'laravel_denials.php:unauthenticated_'.$code,
            ];
        }
    }
}
if ($expected === 0) {
    throw new RuntimeException('No authenticated Laravel operations exercised');
}
file_put_contents($argv[2], json_encode($evidence, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR)."\n");
fwrite(STDOUT, $owner.': '.count($evidence).'/'.$expected." unauthenticated route denials measured\n");
if ($failures !== []) {
    fwrite(STDERR, implode("\n", $failures)."\n");
    exit(1);
}
