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
        $expected = $secrets->read(config('planning.credential_file'));
        $outgoing = $secrets->read(config('planning.governance_credential_file'));
        abort_if($expected === null || $outgoing === null || $expected === $outgoing, 503);
        $headers = $request->headers->all('authorization');
        abort_unless(count($headers) === 1 && is_string($headers[0])
            && hash_equals('Bearer '.$expected, $headers[0]), 403);
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
