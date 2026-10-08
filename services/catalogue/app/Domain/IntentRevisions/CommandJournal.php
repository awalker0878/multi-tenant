<?php

declare(strict_types=1);

namespace App\Domain\IntentRevisions;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class CommandJournal
{
    /** Call inside the owning transaction.
     * @return array<string,mixed>|null */
    public static function existing(string $tenant, string $actor, string $key, string $fingerprint): ?array
    {
        DB::select('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', [$tenant.':'.$actor.':'.$key]);
        $row = DB::table('app.catalogue_commands')->where(['tenant_id' => $tenant, 'actor_id' => $actor, 'command_key' => $key])->first();
        if ($row === null) {
            return null;
        }
        if (! hash_equals($row->fingerprint, $fingerprint)) {
            throw new IntentFailure('idempotency_conflict', 409, 'command_key');
        }

        return json_decode($row->response, true, 512, JSON_THROW_ON_ERROR);
    }

    /**
     * @param array<string,mixed> $response */
    public static function complete(string $tenant, string $actor, string $key, string $fingerprint, array $response): void
    {
        DB::table('app.catalogue_commands')->insert(['tenant_id' => $tenant, 'actor_id' => $actor, 'command_key' => $key, 'fingerprint' => $fingerprint, 'response' => json_encode($response, JSON_THROW_ON_ERROR)]);
    }

    public static function event(string $tenant, string $actor, string $resource, int $version, string $type, ?string $revision = null, ?string $digest = null): void
    {
        $id = (string) Str::uuid();
        $envelope = CanonicalJson::encode(['schema_version' => 1, 'event_id' => $id, 'tenant_id' => $tenant, 'actor_id' => $actor, 'resource_id' => $resource, 'sequence' => $version, 'event_type' => $type, 'revision_id' => $revision, 'digest' => $digest, 'occurred_at' => now()->toIso8601String()]);
        DB::table('app.catalogue_audit')->insert(['event_id' => $id, 'tenant_id' => $tenant, 'actor_id' => $actor, 'resource_id' => $resource, 'sequence' => $version, 'event_type' => $type, 'envelope' => $envelope]);
        DB::table('app.catalogue_outbox')->insert(['event_id' => $id, 'envelope' => $envelope, 'resource_id' => $resource, 'sequence' => $version]);
    }
}
