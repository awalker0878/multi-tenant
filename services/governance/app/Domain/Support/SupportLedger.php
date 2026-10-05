<?php

declare(strict_types=1);

namespace App\Domain\Support;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class SupportLedger
{
    /** @param array<string, mixed> $facts */
    public static function record(string $tenant, ?string $actor, string $event, string $resource, int $revision, array $facts = []): void
    {
        $id = (string) Str::uuid();
        $correlation = (string) Str::uuid();
        $payload = json_encode(['event_id' => $id, 'tenant_id' => $tenant, 'actor_id' => $actor,
            'resource_id' => $resource, 'revision' => $revision, 'correlation_id' => $correlation,
            'policy_version' => SupportPolicy::VERSION, 'facts' => $facts], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
        $entry = ['id' => $id, 'tenant_id' => $tenant, 'event' => $event, 'payload_json' => $payload, 'occurred_at' => now()];
        DB::table('app.support_audit')->insert($entry + ['actor_id' => $actor, 'resource_id' => $resource, 'revision' => $revision, 'correlation_id' => $correlation]);
        DB::table('app.support_outbox')->insert($entry);
    }
}
