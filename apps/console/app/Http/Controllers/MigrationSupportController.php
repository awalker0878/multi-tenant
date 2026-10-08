<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Planning\PlanningFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

final class MigrationSupportController
{
    public function show(Request $request, string $tenant, string $application, string $environment, string $site, PlanningGateway $planning): Response
    {
        $support = $this->read($request, $tenant, $application, $environment, $site, $planning);
        Inertia::clearHistory();

        return Inertia::render('planning/MigrationSupport', ['tenantId' => $tenant, 'siteId' => $site, 'applicationId' => $application, 'environment' => $environment, 'support' => $support]);
    }

    public function status(Request $request, string $tenant, string $application, string $environment, string $site, PlanningGateway $planning): JsonResponse
    {
        return response()->json(['available' => true, 'support' => $this->read($request, $tenant, $application, $environment, $site, $planning)])->header('Cache-Control', 'no-store, private');
    }

    private function read(Request $request, string $tenant, string $application, string $environment, string $site, PlanningGateway $planning): array
    {
        $session = $request->session()->get('identity.token');
        if (! is_string($session)) {
            throw new PlanningFailure(403, 'access_unavailable');
        }

        return $planning->call($session, $tenant, $application, $environment, 'POST', 'migration-support', [$site], ['site_id' => $site]);
    }
}
