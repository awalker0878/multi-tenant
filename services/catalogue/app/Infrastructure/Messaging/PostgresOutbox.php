<?php

declare(strict_types=1);

namespace App\Infrastructure\Messaging;

use App\Application\Messaging\Contracts\FactWriter;
use InvalidArgumentException;
use PDO;
use Throwable;

final readonly class PostgresOutbox implements FactWriter
{
    public function __construct(private PDO $database, private EventCodec $codec) {}

    public function append(string $wire, string $payload, string $tenant, string $actor): string
    {
        $event = $this->codec->decode($wire);
        if ($event->tenant_id !== $tenant || $event->actor_id !== $actor
            || strlen($payload) > 2048 || ! hash_equals($event->payload_sha256, hash('sha256', $payload))) {
            throw new InvalidArgumentException('fact_scope_or_digest_mismatch');
        }
        $canonical = $this->codec->canonical($event);
        $this->database->beginTransaction();
        try {
            $this->database->exec("SET LOCAL statement_timeout = '3s'");
            $insert = $this->database->prepare('INSERT INTO app.messaging_facts(event_id, tenant_id, record_id, revision, payload, envelope) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (event_id) DO NOTHING RETURNING event_id');
            $insert->execute([$event->event_id, $tenant, $event->record_id, $event->revision, $payload, $canonical]);
            if ($insert->fetchColumn() === false) {
                $existing = $this->database->prepare('SELECT envelope FROM app.messaging_facts WHERE event_id = ?');
                $existing->execute([$event->event_id]);
                if ($existing->fetchColumn() !== $canonical) {
                    throw new InvalidArgumentException('idempotency_conflict');
                }
                $this->database->commit();

                return 'duplicate';
            }
            $outbox = $this->database->prepare('INSERT INTO app.messaging_outbox(event_id, envelope) VALUES (?, ?)');
            $outbox->execute([$event->event_id, $canonical]);
            $this->database->commit();

            return 'recorded';
        } catch (Throwable $error) {
            if ($this->database->inTransaction()) {
                $this->database->rollBack();
            }
            throw $error;
        }
    }

    public function dispatchOne(ConfirmedPublisher $publisher): bool
    {
        // One bounded transaction is the recoverable claim. A killed relay loses
        // its row lock; uncertain publish outcomes leave the same event pending.
        $this->database->beginTransaction();
        try {
            $this->database->exec("SET LOCAL statement_timeout = '3s'");
            $this->database->exec("SET LOCAL idle_in_transaction_session_timeout = '15s'");
            $statement = $this->database->query('SELECT event_id, envelope FROM app.messaging_outbox WHERE published_at IS NULL ORDER BY queued_at, event_id FOR UPDATE SKIP LOCKED LIMIT 1');
            $row = $statement === false ? false : $statement->fetch(PDO::FETCH_ASSOC);
            if (! is_array($row)) {
                $this->database->commit();

                return false;
            }
            $publisher->publish((string) $row['envelope'], (string) $row['event_id']);
            $update = $this->database->prepare('UPDATE app.messaging_outbox SET published_at = clock_timestamp() WHERE event_id = ?');
            $update->execute([$row['event_id']]);
            $this->database->commit();

            return true;
        } catch (Throwable $error) {
            if ($this->database->inTransaction()) {
                $this->database->rollBack();
            }
            throw $error;
        }
    }
}
