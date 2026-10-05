<?php

declare(strict_types=1);

namespace App\Domain\Identity;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class IdentityLedger
{
    // Called inside the owning state transition's transaction. No credential payloads.
    public static function record(string $event, string $actor = 'bootstrap-admin'): void
    {
        $entry = ['id' => (string) Str::uuid(), 'event' => $event, 'occurred_at' => now()];
        DB::table('app.identity_audit')->insert($entry + ['actor' => $actor]);
        DB::table('app.identity_outbox')->insert($entry);
    }
}
