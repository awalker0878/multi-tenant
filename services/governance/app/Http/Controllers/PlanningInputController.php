<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Identity\Actions\InspectActorDelegation;
use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

final class PlanningInputController
{
    public function __invoke(Request $request, string $tenant, InspectActorDelegation $inspect, AuthorizeTenant $authority): JsonResponse
    {
        $owner = $request->attributes->get('verified_service');
        if (! in_array($owner, ['catalogue', 'inventory', 'assurance'], true) || array_diff(array_keys($request->all()), ['action', 'scope']) !== []) {
            throw new IdentityDenied('forbidden', 403);
        }
        $input = $request->validate(['action' => ['required', 'in:plan.read,plan.create'], 'scope' => ['required', 'array:site_id,environment,resource_id'],
            'scope.site_id' => ['required', 'uuid', 'lowercase'], 'scope.environment' => ['required', 'uuid', 'lowercase'], 'scope.resource_id' => ['required', 'uuid', 'lowercase']]);
        $headers = $request->headers->all('x-actor-delegation');
        if (count($headers) !== 1 || ! is_string($headers[0])) {
            throw new IdentityDenied('forbidden', 403);
        }
        $decision = $inspect->handle('planning', $headers[0], $tenant, $input['action'], $input['scope']);
        $actor = new FederatedIdentity($decision['actor_id'], false);
        $authority->handle($actor, $tenant, 'application.read', ['site_id' => null, 'environment' => $input['scope']['environment'], 'resource_id' => $input['scope']['resource_id']]);
        $authority->handle($actor, $tenant, 'inventory.read', ['site_id' => $input['scope']['site_id'], 'environment' => null, 'resource_id' => null]);

        return response()->json($decision + ['source_owner' => $owner, 'source_use' => 'planning_read_only'])->header('Cache-Control', 'no-store, private');
    }
}
