<?php

declare(strict_types=1);

namespace App\Application\Recovery\Actions;

use App\Application\Recovery\Contracts\RecoveryCustody;
use App\Application\Recovery\Contracts\RecoveryDatabase;
use App\Application\Recovery\RecoveryPlan;
use App\Application\Recovery\RecoveryState;
use App\Application\Support\Contracts\SupportTrust;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Recovery\RecoveryJson;
use App\Domain\Support\SupportLedger;
use Illuminate\Support\Facades\DB;

final class ApplyIdentityRecovery
{
    public function __construct(private readonly RecoveryDatabase $database, private readonly RecoveryCustody $custody,
        private readonly RecoveryPlan $plans, private readonly RecoveryState $state, private readonly SupportTrust $trust) {}

    /** @return array<string, mixed> */
    public function handle(string $envelope): array
    {
        if (DB::transactionLevel() !== 0) {
            throw new RecoveryDenied;
        }
        $authorized = $this->custody->authorize($envelope, 'reconcile');
        $trust = $this->database->observe(fn () => $this->trust->current());

        return DB::transaction(function () use ($envelope, $authorized, $trust): array {
            $this->database->lock();
            $plan = $authorized['payload'];
            if (! is_array($plan['observations'] ?? null) || ! is_string($plan['recovery_id'] ?? null)
                || $trust->connectionRevision !== DB::table('app.oidc_installation')->where('id', 1)->value('active_revision')
                || now()->getTimestamp() - $trust->observedAt > 5) {
                throw new RecoveryDenied;
            }
            $expected = $this->plans->build($plan['observations'], $plan['recovery_id'], $plan['created_at'], $plan['expires_at'], $trust->keyThumbprints);
            if (RecoveryJson::encode($expected) !== RecoveryJson::encode($plan)) {
                throw new RecoveryDenied;
            }
            $counts = [];
            foreach (['identity_sessions', 'federated_sessions', 'actor_delegations'] as $table) {
                $counts[$table] = DB::table('app.'.$table)->whereNull('revoked_at')->update(['revoked_at' => now()]);
            }
            foreach (['oidc_flows', 'oidc_verifications'] as $table) {
                $counts[$table] = DB::table('app.'.$table)->whereNull('consumed_at')->update(['consumed_at' => now()]);
            }
            foreach (['delegated_grants', 'support_security_grants'] as $table) {
                $counts[$table] = DB::table('app.'.$table)->whereNull('revoked_at')->update(['revoked_at' => now(), 'revision' => DB::raw('revision + 1')]);
            }
            $counts['approvals'] = DB::table('app.approvals')->whereIn('state', ['requested', 'approved'])->update(['state' => 'revoked', 'revision' => DB::raw('revision + 1')]);
            $counts['support_requests'] = 0;
            foreach (DB::table('app.support_requests')->whereIn('state', ['requested', 'approved', 'active'])->get() as $request) {
                DB::table('app.support_requests')->where('id', $request->id)->update(['state' => 'invalidated', 'revision' => $request->revision + 1]);
                SupportLedger::record($request->tenant_id, null, 'support.access.invalidated', $request->id, $request->revision + 1, ['recovery_id' => $plan['recovery_id']]);
                $counts['support_requests']++;
            }
            $members = array_map(fn (array $item): string => $item['membership']['id'], $expected['memberships']);
            $tenants = array_values(array_unique(array_map(fn (array $item): string => $item['membership']['tenant_id'], $expected['memberships'])));
            $counts['memberships_reconciled'] = count($members);
            $counts['memberships_revoked'] = DB::table('app.tenant_memberships')->where('state', 'active')->whereNotIn('id', $members)
                ->update(['state' => 'revoked', 'revision' => DB::raw('revision + 1')]);
            DB::table('app.tenant_memberships')->whereIn('id', $members)->update(['revision' => DB::raw('revision + 1')]);
            $counts['tenants_suspended'] = DB::table('app.tenants')->where('state', 'active')->whereNotIn('id', $tenants)
                ->update(['state' => 'suspended', 'revision' => DB::raw('revision + 1')]);
            DB::table('app.tenants')->whereIn('id', $tenants)->update(['revision' => DB::raw('revision + 1')]);
            DB::table('app.bootstrap_administrator')->where('id', 1)->update(['password_hash' => null, 'credential_version' => DB::raw('credential_version + 1')]);
            DB::table('app.oidc_installation')->where('id', 1)->update(['latest_revision' => $expected['federation']['revision']]);
            DB::table('app.identity_admission')->where('id', 1)->update(['binding_sha256' => $expected['binding_sha256']]);
            $after = RecoveryJson::digest($this->state->snapshot());
            $receipt = ['id' => $expected['recovery_id'], 'binding_sha256' => $expected['binding_sha256'],
                'plan_sha256' => RecoveryJson::digest($expected), 'post_snapshot_sha256' => $after,
                'envelope_json' => $envelope, 'counts_json' => RecoveryJson::encode($counts), 'applied_at' => now()];
            DB::table('app.identity_recovery_receipts')->insert($receipt);
            $current = $this->custody->held();
            if ($current->descriptor !== $expected['descriptor_sha256'] || $current->trust !== $expected['trust_sha256']
                || $current->code !== $expected['code_sha256'] || $current->workloads !== $expected['workloads']) {
                throw new RecoveryDenied;
            }
            $this->custody->authorize($envelope, 'reconcile');

            // This reports only a committed, still-held reconciliation; it is not resumption.
            return ['recovery_id' => $expected['recovery_id'], 'plan_sha256' => $receipt['plan_sha256'],
                'post_snapshot_sha256' => $after, 'counts' => $counts, 'admission' => 'HELD'];
        });
    }
}
