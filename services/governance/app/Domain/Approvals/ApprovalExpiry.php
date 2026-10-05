<?php

declare(strict_types=1);

namespace App\Domain\Approvals;

use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use stdClass;

final class ApprovalExpiry
{
    /** Caller holds the common admission lock and the approval row lock. */
    public static function apply(stdClass $approval): bool
    {
        if (! in_array($approval->state, ['requested', 'approved'], true) || Carbon::parse($approval->expires_at)->isFuture()) {
            return false;
        }
        $approval->state = 'expired';
        $approval->revision++;
        DB::table('app.approvals')->where('id', $approval->id)->where('tenant_id', $approval->tenant_id)
            ->update(['state' => 'expired', 'revision' => $approval->revision]);
        GovernanceLedger::record($approval->tenant_id, null, 'governance.approval.expired', $approval->id, $approval->revision,
            ['plan_digest' => $approval->plan_digest, 'trigger' => 'approval_deadline']);

        return true;
    }
}
