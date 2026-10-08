<?php

declare(strict_types=1);

namespace App\Application\Qualification\Actions;

use App\Application\Qualification\Contracts\ConfirmedInvalidationPublisher;
use Illuminate\Support\Facades\DB;
use RuntimeException;

/**
 * Deliver one durable invalidation in scope/epoch order. Failed, timed out, or
 * ambiguous acknowledgements leave the same event pending for a safe replay.
 */
final readonly class DeliverQualificationInvalidation
{
    public function __construct(private ConfirmedInvalidationPublisher $publisher) {}

    /** @return 'idle'|'delivered' */
    public function handle(): string
    {
        return DB::transaction(function (): string {
            DB::statement("SET LOCAL statement_timeout = '10s'");
            DB::statement("SET LOCAL idle_in_transaction_session_timeout = '15s'");
            $row = DB::selectOne(<<<'SQL'
                SELECT pending.event_id, pending.scope_sha256, pending.authority_epoch, pending.payload
                  FROM app.qualification_authority_outbox pending
                 WHERE pending.delivered_at IS NULL
                   AND NOT EXISTS (
                        SELECT 1 FROM app.qualification_authority_outbox earlier
                         WHERE earlier.scope_sha256 = pending.scope_sha256
                           AND earlier.authority_epoch < pending.authority_epoch
                           AND earlier.delivered_at IS NULL
                   )
                 ORDER BY pending.created_at, pending.scope_sha256, pending.authority_epoch
                 LIMIT 1
                 FOR UPDATE OF pending SKIP LOCKED
                SQL);
            if ($row === null) {
                return 'idle';
            }
            $event = json_decode((string) $row->payload, true, 64, JSON_THROW_ON_ERROR);
            if (! is_array($event)
                || ($event['event_id'] ?? null) !== (string) $row->event_id
                || ($event['scope_sha256'] ?? null) !== $row->scope_sha256
                || ($event['authority_epoch'] ?? null) !== (int) $row->authority_epoch
                || ! is_string($event['event_sha256'] ?? null)) {
                throw new RuntimeException('qualification_invalidation_invalid');
            }

            // Publisher must obtain an explicit durable, scope-bound inbox receipt;
            // a timeout after acceptance will deliberately replay this same event.
            $this->publisher->publish($event);
            $updated = DB::table('app.qualification_authority_outbox')
                ->where('event_id', $row->event_id)
                ->whereNull('delivered_at')
                ->update(['delivered_at' => time()]);
            if ($updated !== 1) {
                throw new RuntimeException('qualification_invalidation_ack_raced');
            }

            return 'delivered';
        }, 3);
    }
}
