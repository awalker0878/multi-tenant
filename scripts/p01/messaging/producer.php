<?php
// Disposable campaign adapter. It invokes the independently built Catalogue code.
declare(strict_types=1);
require '/app/vendor/autoload.php';
use App\Application\Messaging\Actions\RecordFoundationFact;
use App\Infrastructure\Messaging\ConfirmedPublisher;
use App\Infrastructure\Messaging\EventCodec;
use App\Infrastructure\Messaging\PostgresOutbox;
use App\Infrastructure\Messaging\RabbitPublisher;

$secret = static fn (string $name): string => trim(file_get_contents('/run/secrets/'.$name));
$db = new PDO('pgsql:host=postgres;port=5432;dbname=catalogue;sslmode=verify-full;sslrootcert=/run/secrets/ca.crt', 'catalogue_runtime', $secret('db-password'), [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 2]);
$outbox = new PostgresOutbox($db, new EventCodec);
$input = json_decode(stream_get_contents(STDIN), true, flags: JSON_THROW_ON_ERROR);
try {
    if ($input['operation'] === 'record') {
        $result = (new RecordFoundationFact($outbox))->handle(json_encode($input['event'], JSON_THROW_ON_ERROR), $input['payload'], $input['tenant'], $input['actor']);
    } else {
        $publisher = new RabbitPublisher('rabbit', $secret('broker-password'), '/run/secrets/ca.crt');
        if ($input['operation'] === 'crash-after-publish') {
            $publisher = new class($publisher) implements ConfirmedPublisher {
                public function __construct(private ConfirmedPublisher $inner) {}
                public function publish(string $wire, string $eventId): void {
                    $this->inner->publish($wire, $eventId);
                    exit(91); // Process loss: PostgreSQL must release the uncommitted row claim.
                }
            };
        }
        $result = $outbox->dispatchOne($publisher) ? 'published' : 'empty';
    }
    echo json_encode(['result' => $result], JSON_THROW_ON_ERROR).PHP_EOL;
} catch (Throwable $error) {
    // Retain only allowlisted reasons; never serialize driver errors or credentials.
    $reason = $error instanceof InvalidArgumentException ? $error->getMessage() : 'dependency_failure';
    echo json_encode(['result' => 'rejected', 'reason' => $reason], JSON_THROW_ON_ERROR).PHP_EOL;
    exit(2);
}
