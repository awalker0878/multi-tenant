<?php

declare(strict_types=1);

// Disposable PostgreSQL concurrency driver; never shipped in a service image.
// The parent supplies synthetic trust observations. Real adapter/TLS checks run separately.
use App\Application\Support\Actions\DecideSupportAccess;
use App\Application\Support\Actions\UseSupportAccess;
use App\Application\Support\Contracts\SupportTrust;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportTrustState;
use Illuminate\Contracts\Console\Kernel;

$root = dirname(__DIR__, 2).'/services/governance';
require $root.'/vendor/autoload.php';
$app = require $root.'/bootstrap/app.php';
$app->make(Kernel::class)->bootstrap();
if (getenv('P02_TEST_POSTGRES') !== '1' || getenv('DB_DATABASE') !== 'p02_identity_test') {
    exit(2);
}
$input = json_decode(stream_get_contents(STDIN), true, 32, JSON_THROW_ON_ERROR);
config(['identity.admission_file' => $input['admission_file'], 'identity.console_credential_file' => $input['credential_file']]);
$app->instance(SupportTrust::class, new class($input['trust']) implements SupportTrust
{
    public function __construct(private array $trust) {}

    public function current(): SupportTrustState
    {
        return new SupportTrustState($this->trust['connectionRevision'], $this->trust['keyThumbprints'], time());
    }
});
try {
    $action = $input['operation'] === 'inspect' ? UseSupportAccess::class : DecideSupportAccess::class;
    app($action)->handle($input['token'], trim(file_get_contents($input['credential_file'])), $input['tenant'], $input['id'], $input['operation'], $input['key'], $input['body']);
    echo 'committed'.PHP_EOL;
} catch (IdentityDenied $error) {
    echo $error->reason.PHP_EOL;
}
