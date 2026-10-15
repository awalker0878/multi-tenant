<?php

declare(strict_types=1);

namespace App\Domain\Identity;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class IdentityLedger
{
    /** @param array<string, string> $payload */
    public static function command(string $actor, string $operation, string $key, #[\SensitiveParameter] string $workload, #[\SensitiveParameter] array $payload, ?string $sessionHash = null, bool $replaySafe = false): bool
    {
        if (DB::transactionLevel() === 0 || ! preg_match('/\A[a-f0-9]{32,64}\z/', $key)) {
            throw new IdentityDenied('idempotency_key_invalid', 422);
        }
        $binding = DB::table('app.identity_admission')->where('id', 1)->value('binding_sha256');
        if (! is_string($binding) || ! preg_match('/\A[a-f0-9]{64}\z/', $binding)) {
            throw new IdentityDenied('identity_recovery_required', 503);
        }
        // These operations are installation-scoped: null is not a tenant ID.
        // Actor/session/workload and custody are independently derived by the owner.
        $scope = hash('sha256', json_encode(['tenant_id' => null, 'actor_id' => $actor,
            'operation_id' => $operation, 'installation_binding' => $binding,
            'workload_sha256' => hash('sha256', $workload), 'session_sha256' => $sessionHash], JSON_THROW_ON_ERROR));
        ksort($payload);
        // Keyed fingerprints prevent retained password digests from becoming an offline oracle.
        $fingerprint = hash_hmac('sha256', json_encode($payload, JSON_THROW_ON_ERROR), $workload);
        $keyHash = hash('sha256', $key);
        $prior = DB::table('app.identity_command_keys')->where('scope_sha256', $scope)->where('key_sha256', $keyHash)->first();
        if ($prior !== null) {
            if (! hash_equals($prior->request_sha256, $fingerprint) || now()->gte($prior->expires_at) || ! $replaySafe) {
                throw new IdentityDenied('identity_command_conflict', 409);
            }

            return false;
        }
        DB::table('app.identity_command_keys')->where('expires_at', '<', now()->subSeconds(604800))->delete();
        DB::table('app.identity_command_keys')->insert(['scope_sha256' => $scope, 'key_sha256' => $keyHash,
            'request_sha256' => $fingerprint, 'expires_at' => now()->addSeconds(604800)]);

        return true;
    }

    // Called inside the owning state transition's transaction. No credential payloads.
    public static function record(string $event, string $actor = 'bootstrap-admin'): void
    {
        $entry = ['id' => (string) Str::uuid(), 'event' => $event, 'occurred_at' => now()];
        DB::table('app.identity_audit')->insert($entry + ['actor' => $actor]);
        DB::table('app.identity_outbox')->insert($entry);
    }
}
