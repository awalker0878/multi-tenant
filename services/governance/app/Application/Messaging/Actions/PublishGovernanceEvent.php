<?php

declare(strict_types=1);

namespace App\Application\Messaging\Actions;

use App\Application\Messaging\Contracts\ConfirmedPublisher;
use App\Application\Messaging\Contracts\EventEncoder;
use App\Domain\Messaging\InvalidEvent;
use Illuminate\Support\Facades\DB;
use Throwable;

final class PublishGovernanceEvent
{
    public function __construct(private readonly ConfirmedPublisher $publisher, private readonly EventEncoder $encoder) {}

    public function handle(): string
    {
        return DB::transaction(function (): string {
            // A killed relay releases its database claim. A lost confirmation can
            // replay the same immutable event; consumers must use durable inboxes.
            if (DB::getDriverName() === 'pgsql') {
                DB::statement("SET LOCAL statement_timeout = '3s'");
                DB::statement("SET LOCAL idle_in_transaction_session_timeout = '30s'");
            }
            $row = DB::table('app.governance_outbox')->whereNull('published_at')->whereNull('quarantined_at')
                ->where('available_at', '<=', now())->orderBy('occurred_at')->orderBy('id')
                ->lock(DB::getDriverName() === 'pgsql' ? 'FOR UPDATE SKIP LOCKED' : true)->first();
            if ($row === null) {
                return 'idle';
            }
            $record = DB::table('app.governance_outbox')->where('id', $row->id);
            try {
                $wire = $this->encoder->encode($row);
            } catch (InvalidEvent) {
                $record->update(['quarantined_at' => now(), 'last_error' => 'invalid_event']);

                return 'quarantined';
            }
            try {
                $this->publisher->publish($wire, $row->id, $row->event.'.v1');
            } catch (Throwable) {
                // Never retain broker exception text: it may contain credentials.
                $attempts = min($row->attempts + 1, 1000000);
                $record->update(['attempts' => $attempts, 'last_error' => 'publication_unconfirmed',
                    'available_at' => now()->addSeconds(min(300, 2 ** min($attempts, 9)))]);

                return 'retry';
            }
            $record->update(['published_at' => now(), 'last_error' => null]);

            return 'published';
        });
    }
}
