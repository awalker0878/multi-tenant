<?php

declare(strict_types=1);

if (getenv('GITHUB_ACTIONS') !== 'true' || getenv('P03_TEST_POSTGRES') !== '1') {
    exit(2);
}
$root = dirname(__DIR__, 2);
require $root.'/apps/console/vendor/autoload.php';
$app = require $root.'/apps/console/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$fixture = json_decode(file_get_contents($argv[1]), true, 512, JSON_THROW_ON_ERROR);
foreach (['admin', 'author'] as $actor) {
    // Each browser gets an independent session store. Reusing the previous store
    // would invalidate the administrator's newly saved session on the second loop.
    app('session')->forgetDrivers();
    $session = app('session')->driver();
    $session->start();
    $session->invalidate();
    $session->put('identity.token', $fixture[$actor.'_token']);
    $session->regenerateToken();
    $session->save();
    $name = $session->getName();
    $fixture[$actor.'_cookie'] = ['name' => $name, 'value' => app('encrypter')->encrypt(
        Illuminate\Cookie\CookieValuePrefix::create($name, app('encrypter')->getKey()).$session->getId(), false),
        'url' => 'http://127.0.0.1:8031', 'httpOnly' => true, 'secure' => false, 'sameSite' => 'Lax'];
}
file_put_contents($argv[1], json_encode($fixture, JSON_THROW_ON_ERROR));
chmod($argv[1], 0600);
echo "Disposable Console sessions persisted.\n";
