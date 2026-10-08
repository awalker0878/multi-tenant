<?php

declare(strict_types=1);

if (getenv('GITHUB_ACTIONS') !== 'true' || getenv('P03_TEST_POSTGRES') !== '1') {
    exit(2);
}
$root = dirname(__DIR__, 2);
require $root.'/services/catalogue/vendor/autoload.php';
$app = require $root.'/services/catalogue/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
if ($argv[1] === 'uncertain') {
    // Simulate termination after a real broker confirmation but before local commit.
    $real = app(App\Infrastructure\Messaging\RabbitCataloguePublisher::class);
    $action = new App\Application\Messaging\Actions\PublishCatalogueEvent(new class($real) implements App\Application\Messaging\Contracts\CataloguePublisher {
        public function __construct(private App\Infrastructure\Messaging\RabbitCataloguePublisher $real) {}
        public function publish(string $wire, string $eventId): void {
            $this->real->publish($wire, $eventId);
            throw new RuntimeException('synthetic_after_confirmation');
        }
    });
    try { $action->handle(); } catch (RuntimeException $e) {
        if ($e->getMessage() !== 'synthetic_after_confirmation') { throw $e; }
        echo "Confirmed event retained for replay.\n";
        exit(0);
    }
    exit(1);
}
$config = new PhpAmqpLib\Connection\AMQPConnectionConfig;
$config->setHost('127.0.0.1');
$config->setPort(5679);
$config->setUser($argv[1] === 'denied' ? 'catalogue' : 'p03-observer');
$config->setPassword(trim(file_get_contents(getenv($argv[1] === 'denied' ? 'CATALOGUE_BROKER_PASSWORD_FILE' : 'P03_OBSERVER_PASSWORD_FILE'))));
$config->setVhost('product');
$config->setIsSecure(true);
$config->setSslCaCert(getenv('CATALOGUE_BROKER_CA_FILE'));
$config->setSslVerify(true);
$config->setSslVerifyName(true);
$config->setConnectionTimeout(2.0);
$config->setReadTimeout(5.0);
$config->setWriteTimeout(5.0);
$config->setHeartbeat(0);
$connection = PhpAmqpLib\Connection\AMQPConnectionFactory::create($config);
try {
    $channel = $connection->channel();
    if ($argv[1] === 'denied') {
        try { $channel->basic_get('p03.observer', false); }
        catch (PhpAmqpLib\Exception\AMQPProtocolChannelException $e) {
            if ($e->getCode() !== 403) { throw $e; }
            echo "Publisher cannot read consumer queue.\n";
            exit(0);
        }
        exit(1);
    }
    $events = [];
    while (($message = $channel->basic_get('p03.observer', false)) !== null) {
        $events[] = ['message_id' => $message->get('message_id'), 'body' => json_decode($message->getBody(), true, 512, JSON_THROW_ON_ERROR)];
        $message->ack();
    }
    file_put_contents($argv[2], json_encode($events, JSON_THROW_ON_ERROR));
    echo json_encode(['observed' => count($events)])."\n";
} finally {
    $connection->close();
}
