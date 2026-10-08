<?php

declare(strict_types=1);

namespace App\Application\Messaging\Actions;

use App\Application\Messaging\Contracts\CataloguePublisher;
use Illuminate\Support\Facades\DB;

final class PublishCatalogueEvent
{
    public function __construct(private readonly CataloguePublisher $publisher) {}

    public function handle(): bool
    {
        return DB::transaction(function (): bool {
            DB::statement("SET LOCAL statement_timeout='3s'");
            DB::statement("SET LOCAL idle_in_transaction_session_timeout='15s'");
            $rows = DB::select('SELECT o.event_id,o.envelope FROM app.catalogue_outbox o WHERE o.published_at IS NULL AND NOT EXISTS (SELECT 1 FROM app.catalogue_outbox earlier WHERE earlier.resource_id=o.resource_id AND earlier.sequence<o.sequence AND earlier.published_at IS NULL) ORDER BY o.queued_at,o.event_id FOR UPDATE OF o SKIP LOCKED LIMIT 1');
            if ($rows === []) {
                return false;
            }
            $row = $rows[0];
            $this->publisher->publish($row->envelope, $row->event_id);
            DB::table('app.catalogue_outbox')->where('event_id', $row->event_id)->update(['published_at' => now()]);

            return true;
        });
    }
}
