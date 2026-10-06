<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Planning\Contracts\PlanningInputAuthority;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

final class PlanningInputController
{
    public function __invoke(Request $request, string $tenant, string $application, string $environment, string $site, string $revision, PlanningInputAuthority $authority): JsonResponse
    {
        $authority->check($request->headers->all(), $tenant, ['site_id' => $site, 'environment' => $environment, 'resource_id' => $application]);
        $row = DB::table('app.catalogue_revisions as r')->join('app.catalogue_deployments as d', function ($j): void {
            $j->on('r.tenant_id', '=', 'd.tenant_id')->on('r.deployment_id', '=', 'd.id');
        })->where(['r.tenant_id' => $tenant, 'r.application_id' => $application, 'r.id' => $revision, 'd.environment_id' => $environment])->first(['r.*']);
        abort_if($row === null, 404);

        return response()->json(['id' => $row->id, 'application_id' => $application, 'digest' => $row->digest,
            'intent' => json_decode($row->canonical_intent, true, 64, JSON_THROW_ON_ERROR)])->header('Cache-Control', 'no-store, private');
    }
}
