<?php

declare(strict_types=1);

// Disposable integration-campaign driver, never included in a service image.
use App\Application\Messaging\Actions\PublishGovernanceEvent;
use App\Application\Messaging\Actions\PublishIdentityEvent;
use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Infrastructure\Messaging\RabbitPublisher;
use Illuminate\Contracts\Console\Kernel;

$root = dirname(__DIR__, 2).'/services/governance';
require $root.'/vendor/autoload.php';
$app = require $root.'/bootstrap/app.php';
$app->make(Kernel::class)->bootstrap();
if (getenv('P02_TEST_POSTGRES') !== '1' || getenv('DB_DATABASE') !== 'p02_identity_test') {
    exit(2);
}
if (($argv[1] ?? '') === 'crash') {
    $app->instance(ConfirmedPublisher::class, new class implements ConfirmedPublisher
    {
        public function publish(string $wire, string $eventId, string $routingKey): void
        {
            (new RabbitPublisher)->publish($wire, $eventId, $routingKey);
            // Real broker confirmation, followed by process death before DB ack.
            exit(91);
        }
    });
}
echo app(($argv[2] ?? '') === 'identity' ? PublishIdentityEvent::class : PublishGovernanceEvent::class)->handle().PHP_EOL;
