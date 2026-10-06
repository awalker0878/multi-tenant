<?php

declare(strict_types=1);

namespace App\Application\Recovery;

use App\Application\Recovery\Contracts\RecoveryCustody;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Recovery\RecoveryJson;
use Illuminate\Support\Facades\DB;

final class RecoveryPlan
{
    public function __construct(private readonly RecoveryCustody $custody, private readonly RecoveryState $state) {}

    /** @param array<string, mixed> $observations
     * @param  list<string>  $signers
     * @return array<string, mixed>
     */
    public function build(array $observations, string $id, int $created, int $expires, array $signers): array
    {
        $context = $this->custody->held();
        $federation = $this->state->federation();
        $stored = DB::table('app.identity_admission')->where('id', 1)->value('binding_sha256');
        if (! RecoveryJson::uuid($id) || ! RecoveryJson::hash($stored) || $stored === $context->binding) {
            throw new RecoveryDenied;
        }
        sort($signers, SORT_STRING);

        return ['version' => 1, 'purpose' => 'reconcile', 'recovery_id' => $id, 'created_at' => $created, 'expires_at' => $expires,
            'installation_id' => $context->installation, 'binding_sha256' => $context->binding, 'previous_binding_sha256' => $stored,
            'descriptor_sha256' => $context->descriptor, 'trust_sha256' => $context->trust, 'code_sha256' => $context->code,
            'workloads' => $context->workloads, 'observations' => $observations, 'federation' => $federation,
            'provider_signers' => $signers, 'memberships' => $this->state->memberships($observations, $context->workloads, $federation['issuer']),
            'snapshot' => $this->state->snapshot()];
    }
}
