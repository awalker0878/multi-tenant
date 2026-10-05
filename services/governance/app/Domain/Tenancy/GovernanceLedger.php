<?php

declare(strict_types=1);

namespace App\Domain\Tenancy;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class GovernanceLedger
{
    /** @param array<string, mixed> $facts */
    public static function record(string $tenant, string $actor, string $event, string $resource, int $revision, array $facts): void
    {
        $id = (string) Str::uuid();
        $payload = json_encode(['event_id' => $id, 'tenant_id' => $tenant, 'actor_id' => $actor, 'resource_id' => $resource,
            'revision' => $revision, 'facts' => $facts], JSON_THROW_ON_ERROR);
        $entry = ['id' => $id, 'tenant_id' => $tenant, 'event' => $event, 'payload_json' => $payload, 'occurred_at' => now()];
        DB::table('app.governance_audit')->insert($entry + ['actor_id' => $actor, 'resource_id' => $resource, 'revision' => $revision]);
        DB::table('app.governance_outbox')->insert($entry);
    }

    /** @param array<string, mixed> $value */
    public static function digest(array $value): string
    {
        return hash('sha256', json_encode(self::canonical($value), JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES));
    }

    /** @param array<array-key, mixed> $value
     * @return array<array-key, mixed>
     */
    private static function canonical(array $value): array
    {
        if (! array_is_list($value)) {
            ksort($value, SORT_STRING);
        }
        foreach ($value as $key => $item) {
            if (is_array($item)) {
                $value[$key] = self::canonical($item);
            }
        }

        return $value;
    }
}
