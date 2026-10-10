<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Infrastructure\Foundation\MountedSecret;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/** Service-only latest-revision check; never accepts an operator-supplied revision. */
final class CurrentPlanningIntentController
{
    public function __invoke(Request $request, string $tenant, string $application, string $environment, MountedSecret $secrets): JsonResponse
    {
        $planning = $secrets->read(config('planning.credential_file'));
        $lifecycle = $secrets->read(config('planning.lifecycle_credential_file'));
        $outgoing = $secrets->read(config('planning.governance_credential_file'));
        // Legacy Planning reads remain available before Lifecycle enrolment.
        // When commissioned, the read-only Lifecycle credential is distinct
        // from Planning and Governance; no shared secret grants both audiences.
        abort_if($planning === null || $outgoing === null || $planning === $outgoing
            || ($lifecycle !== null && ($lifecycle === $planning || $lifecycle === $outgoing)), 503);
        $headers = $request->headers->all('authorization');
        $authorized = count($headers) === 1 && is_string($headers[0])
            && (hash_equals('Bearer '.$planning, $headers[0])
                || ($lifecycle !== null && hash_equals('Bearer '.$lifecycle, $headers[0])));
        abort_unless($authorized, 403);
        $row = DB::table('app.catalogue_deployments as d')
            ->join('app.catalogue_revisions as r', function ($j): void {
                $j->on('d.tenant_id', '=', 'r.tenant_id')
                    ->on('d.current_revision_id', '=', 'r.id');
            })
            ->where([
                'd.tenant_id' => $tenant, 'd.application_id' => $application,
                'd.environment_id' => $environment, 'r.application_id' => $application,
            ])
            ->first(['r.id', 'r.digest', 'r.canonical_intent']);
        abort_if($row === null, 404);

        return response()->json([
            'revision_id' => $row->id, 'intent_sha256' => $row->digest,
            'intent' => json_decode($row->canonical_intent, true, 64, JSON_THROW_ON_ERROR),
        ])->header('Cache-Control', 'no-store, private');
    }
}
