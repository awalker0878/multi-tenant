<?php

declare(strict_types=1);

namespace App\Application\Recovery;

use App\Application\Recovery\Contracts\RecoveryCustody;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Recovery\RecoveryJson;
use Illuminate\Support\Facades\DB;

final class RecoveryResumption
{
    public function __construct(private readonly RecoveryCustody $custody, private readonly RecoveryState $state) {}

    /** @param list<string> $signers
     * @return array<string, mixed>
     */
    public function build(string $id, int $created, int $expires, array $signers): array
    {
        if (! RecoveryJson::uuid($id)) {
            throw new RecoveryDenied;
        }
        $row = DB::table('app.identity_recovery_receipts')->where('id', $id)->first();
        if ($row === null || DB::table('app.identity_recovery_releases')->where('id', $id)->exists()) {
            throw new RecoveryDenied;
        }
        $context = $this->custody->held();
        $packet = RecoveryJson::decode($row->envelope_json);
        $old = RecoveryJson::decode((string) base64_decode($packet['payload'], true));
        $after = RecoveryJson::digest($this->state->snapshot($id));
        sort($signers, SORT_STRING);
        if ($row->binding_sha256 !== $context->binding || $row->post_snapshot_sha256 !== $after
            || DB::table('app.identity_admission')->where('id', 1)->value('binding_sha256') !== $context->binding
            || $old['descriptor_sha256'] !== $context->descriptor || $old['trust_sha256'] !== $context->trust
            || $old['code_sha256'] !== $context->code || RecoveryJson::digest($old['workloads']) !== RecoveryJson::digest($context->workloads)
            || $old['provider_signers'] !== $signers || RecoveryJson::digest($old['federation']) !== RecoveryJson::digest($this->state->federation())) {
            throw new RecoveryDenied;
        }

        return ['version' => 1, 'purpose' => 'resume', 'recovery_id' => $id, 'created_at' => $created, 'expires_at' => $expires,
            'installation_id' => $context->installation, 'binding_sha256' => $context->binding,
            'descriptor_sha256' => $context->descriptor, 'trust_sha256' => $context->trust, 'code_sha256' => $context->code,
            'workloads' => $context->workloads, 'plan_sha256' => $row->plan_sha256, 'post_snapshot_sha256' => $after,
            'receipt_sha256' => RecoveryJson::digest((array) $row), 'federation' => $old['federation']];
    }
}
