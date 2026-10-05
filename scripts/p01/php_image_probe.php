<?php

declare(strict_types=1);

// Executed by the evidence recorder inside the built image; never installed in it.
function check(bool $condition, string $message): void
{
    if (! $condition) {
        throw new RuntimeException($message);
    }
}

$component = getenv('P01_COMPONENT');
check(is_string($component) && in_array($component, ['governance', 'catalogue', 'assurance', 'console'], true), 'Unknown component');
$status = file_get_contents('/proc/self/status');
check(is_string($status), 'Process status unavailable');
preg_match('/^Uid:\s+(\d+)/m', $status, $uid);
preg_match('/^Gid:\s+(\d+)/m', $status, $gid);
preg_match('/^CapEff:\s+(\w+)/m', $status, $capabilities);
preg_match('/^NoNewPrivs:\s+(\d+)/m', $status, $privileges);
$rootReadOnly = false;
foreach (file('/proc/self/mountinfo', FILE_IGNORE_NEW_LINES) as $line) {
    $fields = explode(' ', $line);
    if ($fields[4] === '/') {
        $rootReadOnly = in_array('ro', explode(',', $fields[5]), true);
    }
}
$interfaces = array_values(array_diff(scandir('/sys/class/net'), ['.', '..']));
sort($interfaces);
check((int) $uid[1] === 10001 && (int) $gid[1] === 10001, 'Process is not the image non-root identity');
check(hexdec($capabilities[1]) === 0 && (int) $privileges[1] === 1, 'Process privilege limits differ');
check($rootReadOnly && $interfaces === ['lo'], 'Root or network isolation differs');
check(! file_exists('/app/.env') && ! file_exists('/app/bootstrap/cache/config.php'), 'Baked deployment configuration exists');
check(! file_exists('/usr/local/bin/composer') && ! file_exists('/usr/local/bin/node'), 'Build tools leaked into runtime');
check(! is_dir('/app/tests') && ! is_dir('/app/node_modules'), 'Development inputs leaked into runtime');

require '/app/vendor/autoload.php';
$application = require '/app/bootstrap/app.php';
$kernel = $application->make(Illuminate\Contracts\Http\Kernel::class);
$results = [];
foreach (['live' => 200, 'ready' => 503] as $probe => $expectedStatus) {
    $request = Illuminate\Http\Request::create('http://localhost/health/'.$probe, 'GET', server: ['HTTP_ACCEPT' => 'application/json']);
    $response = $kernel->handle($request);
    check($response->getStatusCode() === $expectedStatus, $probe.' returned '.$response->getStatusCode());
    $payload = json_decode($response->getContent(), true, 512, JSON_THROW_ON_ERROR);
    $expected = $probe === 'live'
        ? ['service' => $component, 'status' => 'alive', 'scope' => 'process']
        : ['service' => $component, 'status' => 'not_ready', 'scope' => 'service', 'reason' => 'foundation_only'];
    check($payload === $expected, 'Health payload scope differs');
    check(str_contains($response->headers->get('Cache-Control', ''), 'no-store'), 'Probe response is cacheable');
    $results[$probe] = ['status' => $response->getStatusCode(), 'payload' => $payload];
    $kernel->terminate($request, $response);
}
check($application->environment('production') && $application->make('config')->get('app.debug') === false, 'Runtime configuration is not production-safe');
$class = new ReflectionClass(App\Http\Controllers\HealthController::class);
check(str_starts_with($class->getFileName(), '/app/app/'), 'App namespace resolved outside its owner');

$installed = json_decode(file_get_contents('/app/vendor/composer/installed.json'), true, 512, JSON_THROW_ON_ERROR);
$packages = [];
foreach ($installed['packages'] as $package) {
    $packages[$package['name']] = $package['version'];
}
ksort($packages);
$extensions = get_loaded_extensions();
sort($extensions);
$result = [
    'component' => $component,
    'scope' => 'isolated_http_kernel_process_and_fpm_configuration',
    'php_version' => PHP_VERSION,
    'laravel_version' => Illuminate\Foundation\Application::VERSION,
    'uid' => (int) $uid[1],
    'gid' => (int) $gid[1],
    'capabilities_effective' => hexdec($capabilities[1]),
    'no_new_privileges' => (int) $privileges[1],
    'root_read_only' => $rootReadOnly,
    'network_interfaces' => $interfaces,
    'loaded_extensions' => $extensions,
    'installed_packages' => $packages,
    'health' => $results,
    'native_operations_implemented' => false,
];

if ($component === 'console') {
    check($application->make('config')->get('session.driver') === 'database', 'Console default session store is not shared');
    check($application->make('config')->get('cache.default') === 'database', 'Console default cache store is not shared');
    // This no-network image probe measures markup/assets only. Actual database
    // persistence is verified by the separate Compose/Kubernetes installation.
    $application->make('config')->set('session.driver', 'array');
    $application->make('config')->set('cache.default', 'array');
    $result['console_html_storage_scope'] = 'explicit_in_memory_image_probe';
    $request = Illuminate\Http\Request::create('https://localhost/', 'GET');
    $response = $kernel->handle($request);
    check($response->getStatusCode() === 200, 'Console HTML failed: '.$response->getStatusCode());
    $html = $response->getContent();
    check(str_contains($html, '<div id="app"') && str_contains($html, 'Foundation'), 'Console mount or page descriptor missing');
    check(str_contains($response->headers->get('Content-Type', ''), 'text/html'), 'Console response is not HTML');
    check($response->headers->get('X-Frame-Options') === 'DENY', 'Console frame protection differs');
    check($response->headers->get('X-Content-Type-Options') === 'nosniff', 'Console content-type protection differs');
    $result['console_html'] = ['status' => 200, 'bytes' => strlen($html), 'sha256' => hash('sha256', $html)];
    $kernel->terminate($request, $response);
    $manifestPath = '/app/public/build/manifest.json';
    $manifest = json_decode(file_get_contents($manifestPath), true, 512, JSON_THROW_ON_ERROR);
    check(isset($manifest['resources/js/app.ts']), 'Console entry asset missing from Vite manifest');
    $assets = [];
    foreach ($manifest as $entry) {
        foreach (array_merge([$entry['file']], $entry['css'] ?? []) as $asset) {
            $path = realpath('/app/public/build/'.$asset);
            check(is_string($path) && str_starts_with($path, '/app/public/build/') && is_file($path), 'Missing or escaping built asset');
            $assets[$asset] = ['sha256' => hash_file('sha256', $path), 'bytes' => filesize($path)];
        }
    }
    check(count($assets) >= 2, 'Console JavaScript/CSS bundle incomplete');
    ksort($assets);
    $result['console_assets'] = $assets;
    $result['vite_manifest_sha256'] = hash_file('sha256', $manifestPath);
}

echo json_encode($result, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES).PHP_EOL;
