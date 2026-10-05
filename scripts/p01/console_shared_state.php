<?php
// Disposable campaign adapter; no route is added to the Console.
declare(strict_types=1);
require '/app/vendor/autoload.php';
$app = require '/app/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$input = json_decode(stream_get_contents(STDIN), true, flags: JSON_THROW_ON_ERROR);
$check = static function (bool $pass, string $name) use (&$checks): void {
    $checks[] = ['name' => $name, 'passed' => $pass];
    if (! $pass) {
        throw new RuntimeException($name);
    }
};
$checks = [];
$session = $app->make('session')->driver();
$session->setId(str_repeat('s', 40));
$session->start();
$cache = $app->make('cache')->store('database');
$scoped = new App\Infrastructure\Session\TenantCache($cache, $cache->getStore());
if ($input['stage'] === 'write') {
    $session->put('witness', 'synthetic-private-session');
    $session->save();
    $scoped->put('tenant_a', 'view', 'synthetic-a', 1800);
    $scoped->put('tenant_b', 'view', 'synthetic-b', 1800);
    $check($scoped->lock('tenant_a', 'short-job', 30)->get(), 'initial-lock-acquired');
    $check($scoped->lock('tenant_b', 'short-job', 30)->get(), 'other-tenant-lock-independent');
} else {
    $check($session->get('witness') === 'synthetic-private-session', 'session-survives-process-or-database-restart');
    $check($scoped->get('tenant_a', 'view') === 'synthetic-a', 'tenant-a-cache-restored');
    $check($scoped->get('tenant_b', 'view') === 'synthetic-b', 'tenant-b-cache-isolated');
    $check($scoped->get('tenant_c', 'view') === null, 'foreign-tenant-cache-miss');
    if ($input['stage'] === 'second-process') {
        $other = $scoped->lock('tenant_a', 'short-job', 30);
        $check(! $other->get(), 'second-process-lock-denied');
        $check(! $other->release(), 'foreign-lock-owner-cannot-release');
    }
}
$row = Illuminate\Support\Facades\DB::table('app.sessions')->where('id', str_repeat('s', 40))->first();
$check($row !== null && ! str_contains(base64_decode($row->payload), 'synthetic-private-session'), 'stored-session-is-encrypted');
$check(config('session.driver') === 'database' && config('cache.default') === 'database', 'shared-drivers-selected');
echo json_encode(['result' => 'PASS', 'checks' => $checks], JSON_THROW_ON_ERROR).PHP_EOL;
