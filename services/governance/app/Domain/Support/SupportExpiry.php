<?php

declare(strict_types=1);

namespace App\Domain\Support;

use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use stdClass;

final class SupportExpiry
{
    public static function apply(stdClass $request): void
    {
        if (! in_array($request->state, SupportPolicy::TERMINAL, true)
            && (Carbon::parse($request->expires_at)->lte(now())
                || ($request->effective_until !== null && Carbon::parse($request->effective_until)->lte(now())))) {
            self::end($request, 'expired', null);
        }
    }

    /** @param array<string, mixed> $facts */
    public static function end(stdClass $request, string $state, ?string $actor, array $facts = []): void
    {
        $request->state = $state;
        $request->revision++;
        DB::table('app.support_requests')->where('id', $request->id)->update(['state' => $state, 'revision' => $request->revision]);
        SupportLedger::record($request->tenant_id, $actor, 'support.access.'.$state, $request->id, $request->revision,
            ['binding_sha256' => $request->binding_sha256] + $facts);
    }
}
