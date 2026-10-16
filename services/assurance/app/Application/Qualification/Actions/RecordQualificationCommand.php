<?php

declare(strict_types=1);

namespace App\Application\Qualification\Actions;

use App\Domain\Qualification\NativeQualification;
use Illuminate\Support\Facades\DB;

/** A digest receipt binds a retry; it never caches or grants qualification. */
final class RecordQualificationCommand
{
    /** @param list<string|null> $keys
     * @param array<string, mixed> $body */
    public function handle(string $tenant, string $principal, string $operation, array $keys, array $body): void
    {
        abort_unless(count($keys) === 1 && is_string($keys[0])
            && preg_match('/\A[a-f0-9]{32,64}\z/', $keys[0]) === 1, 422, 'qualification_command_key_invalid');
        abort_unless($principal !== '', 503, 'qualification_principal_unavailable');
        $scope = NativeQualification::digest(['tenant_id' => $tenant, 'actor_id' => $principal, 'operation_id' => $operation]);
        $key = hash('sha256', $keys[0]);
        $request = NativeQualification::digest($body);
        DB::transaction(function () use ($scope, $key, $request): void {
            $now = now()->getTimestamp();
            DB::table('app.qualification_command_keys')->insertOrIgnore([
                'scope_sha256' => $scope, 'key_sha256' => $key,
                'request_sha256' => $request, 'created_at' => $now, 'expires_at' => $now + 604800,
            ]);
            // The unique insert serializes concurrent claims. Receipts are
            // immutable while current; SELECT FOR UPDATE would unnecessarily
            // require UPDATE permission on this digest-only ledger.
            $row = DB::table('app.qualification_command_keys')->where('scope_sha256', $scope)
                ->where('key_sha256', $key)->first();
            abort_unless($row !== null && hash_equals($row->request_sha256, $request)
                && (int) $row->created_at <= $now && (int) $row->expires_at > $now, 409, 'qualification_command_conflict');
            DB::table('app.qualification_command_keys')->where('expires_at', '<', $now - 604800)->delete();
        });
    }
}
