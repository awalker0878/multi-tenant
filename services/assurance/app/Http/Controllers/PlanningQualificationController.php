<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Planning\Contracts\PlanningInputAuthority;
use App\Application\Qualification\Actions\ResolveQualification;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

final class PlanningQualificationController
{
    public function __invoke(Request $request, string $tenant, PlanningInputAuthority $authority): JsonResponse
    {
        abort_if(strlen($request->getContent()) > 32768 || array_diff(array_keys($request->all()), ['scope', 'action', 'qualification_scope']) !== [], 422);
        $input = $request->validate(['scope' => ['required', 'array:site_id,environment,resource_id'],
            'scope.site_id' => ['required', 'uuid', 'lowercase'], 'scope.environment' => ['required', 'uuid', 'lowercase'],
            'scope.resource_id' => ['required', 'uuid', 'lowercase'], 'action' => ['required', 'in:plan.read,plan.create'],
            'qualification_scope' => ['required', 'array:tenant_id,site_id,endpoint_id,native_scope,installed_tuple,action,method,profile_digest,artifacts']]);
        $authority->check($request->headers->all(), $tenant, $input['scope']);
        abort_unless(($input['qualification_scope']['tenant_id'] ?? null) === $tenant && ($input['qualification_scope']['site_id'] ?? null) === $input['scope']['site_id'], 403);
        $result = (new ResolveQualification)->handle($input['qualification_scope']);
        if (! str_ends_with($request->path(), 'planning-qualification-v2')) {
            unset($result['verification']);
            $result['version'] = 1;
        }

        return response()->json($result)->header('Cache-Control', 'no-store, private');
    }
}
