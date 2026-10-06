<?php

declare(strict_types=1);

namespace App\Application\Recovery;

use App\Application\Recovery\Contracts\RecoveryDatabase;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Recovery\RecoveryJson;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;

final class RecoveryState
{
    public function __construct(private readonly RecoveryDatabase $database) {}

    /** @return array<string, array{rows: int, sha256: string}> */
    public function snapshot(?string $recovery = null): array
    {
        $result = [];
        foreach ($this->database->tables() as $table) {
            $query = DB::table('app.'.$table);
            if ($recovery !== null && in_array($table, ['identity_recovery_receipts', 'identity_recovery_releases'], true)) {
                $query->where('id', '!=', $recovery);
            }
            $hashes = [];
            foreach ($query->cursor() as $row) {
                if (count($hashes) >= 100000) {
                    throw new RecoveryDenied;
                }
                $wire = RecoveryJson::encode((array) $row);
                if (strlen($wire) > 1048576) {
                    throw new RecoveryDenied;
                }
                $hashes[] = hash('sha256', $wire);
            }
            sort($hashes, SORT_STRING);
            $result[$table] = ['rows' => count($hashes), 'sha256' => hash('sha256', implode("\n", $hashes))];
        }

        return $result;
    }

    /** @return array<string, mixed> */
    public function federation(): array
    {
        if (DB::table('app.bootstrap_administrator')->where('id', 1)->value('state') !== 'retired') {
            // Recovery can never revive or reset local bootstrap, even with two signatures.
            throw new RecoveryDenied;
        }
        $revision = DB::table('app.oidc_installation')->where('id', 1)->value('active_revision');
        $connection = DB::table('app.oidc_connections')->where('revision', $revision)->first();
        if ($connection === null) {
            throw new RecoveryDenied;
        }
        $cipher = DB::table('app.identity_secrets')->where('id', $connection->secret_ref)->value('ciphertext');
        if (! is_string($cipher) || Crypt::decryptString($cipher) === ''
            || DB::table('app.federated_actors')->where('issuer', $connection->issuer)->where('subject', $connection->administrator_subject)->whereNotNull('disabled_at')->exists()) {
            throw new RecoveryDenied;
        }

        return ['revision' => $revision, 'issuer' => $connection->issuer, 'client_id' => $connection->client_id,
            'administrator_subject' => $connection->administrator_subject, 'redirect_uri' => $connection->redirect_uri,
            'connection_sha256' => RecoveryJson::digest((array) $connection), 'encrypted_secret_sha256' => hash('sha256', $cipher)];
    }

    /** @param array<string, mixed> $observations
     * @param  array<string, string|null>  $workloads
     * @return list<array<string, mixed>>
     */
    public function memberships(array $observations, array $workloads, string $issuer): array
    {
        if (count($observations) !== 6 || ! is_string($observations['case_reference'] ?? null)
            || preg_match('/\A[A-Za-z0-9][A-Za-z0-9._:\/-]{0,127}\z/', $observations['case_reference']) !== 1) {
            throw new RecoveryDenied;
        }
        foreach (['restore_sha256', 'records_sha256', 'containment_sha256'] as $field) {
            if (! RecoveryJson::hash($observations[$field] ?? null)) {
                throw new RecoveryDenied;
            }
        }
        $previous = $observations['previous_workloads'] ?? null;
        if (! is_array($previous) || count($previous) !== count($workloads)) {
            throw new RecoveryDenied;
        }
        foreach ($workloads as $name => $current) {
            if (! array_key_exists($name, $previous) || ($previous[$name] !== null && ! RecoveryJson::hash($previous[$name]))
                || ($name === 'console' && $previous[$name] === null) || ($current !== null && $previous[$name] === $current)) {
                throw new RecoveryDenied;
            }
        }
        $selected = $observations['memberships'] ?? null;
        if (! is_array($selected) || ! array_is_list($selected) || count($selected) > 100) {
            throw new RecoveryDenied;
        }
        $ids = $tenants = $administrators = $memberships = [];
        foreach ($selected as $selection) {
            if (! is_array($selection) || count($selection) !== 2 || ! RecoveryJson::uuid($selection['id'] ?? null)
                || ! RecoveryJson::hash($selection['owner_record_sha256'] ?? null) || in_array($selection['id'], $ids, true)) {
                throw new RecoveryDenied;
            }
            $row = DB::table('app.tenant_memberships')->where('id', $selection['id'])->first();
            $actor = $row === null ? null : DB::table('app.federated_actors')->where('id', $row->actor_id)->first();
            $tenant = $row === null ? null : DB::table('app.tenants')->where('id', $row->tenant_id)->first();
            if ($row === null || $actor === null || $tenant === null || $row->state !== 'active' || $actor->disabled_at !== null
                || $actor->issuer !== $issuer || $tenant->state !== 'active' || ($row->expires_at !== null && Carbon::parse($row->expires_at)->isPast())) {
                throw new RecoveryDenied;
            }
            $ids[] = $row->id;
            $tenants[] = $row->tenant_id;
            if ($row->role === 'tenant_admin' && $row->site_id === null && $row->environment === null && $row->expires_at === null) {
                $administrators[] = $row->tenant_id;
            }
            $memberships[] = ['membership' => (array) $row, 'issuer' => $actor->issuer, 'subject' => $actor->subject,
                'tenant_sha256' => RecoveryJson::digest((array) $tenant), 'owner_record_sha256' => $selection['owner_record_sha256']];
        }
        if (array_diff($tenants, $administrators) !== []) {
            throw new RecoveryDenied;
        }

        return $memberships;
    }
}
