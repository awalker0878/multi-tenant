<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Identity\Actions\InspectActorDelegation;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\PermissionMatrix;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

final class CatalogueOwnerController
{
    public function __invoke(Request $request, string $tenant, InspectActorDelegation $inspect): JsonResponse
    {
        if (array_diff(array_keys($request->all()), ['action', 'scope', 'owners']) !== []) {
            throw ValidationException::withMessages(['request' => 'Unexpected fields.']);
        }
        $input = $request->validate(['action' => ['required', 'in:application.write,reference.write'], 'scope' => ['required', 'array:site_id,environment,resource_id'],
            'scope.site_id' => ['present', 'nullable', 'string', 'max:64'], 'scope.environment' => ['present', 'nullable', 'string', 'max:64'], 'scope.resource_id' => ['present', 'nullable', 'string', 'max:128'],
            'owners' => ['required', 'array', 'min:1', 'max:301'], 'owners.*' => ['required', 'uuid', 'lowercase', 'distinct']]);
        if ($request->attributes->get('verified_service') !== 'catalogue') {
            throw new IdentityDenied('forbidden', 403);
        }
        $tokens = $request->headers->all('x-actor-delegation');
        if (count($tokens) !== 1 || ! is_string($tokens[0])) {
            throw new IdentityDenied('invalid_delegation');
        }
        $inspect->handle('catalogue', $tokens[0], $tenant, $input['action'], $input['scope']);
        $members = DB::table('app.tenant_memberships as m')->join('app.federated_actors as a', 'a.id', '=', 'm.actor_id')
            ->where('m.tenant_id', $tenant)->whereIn('m.actor_id', $input['owners'])->where('m.state', 'active')->whereNull('a.disabled_at')
            ->where(fn ($q) => $q->whereNull('m.expires_at')->orWhere('m.expires_at', '>', now()))->get(['m.actor_id', 'm.site_id', 'm.environment']);
        if ($members->count() !== count($input['owners']) || $members->contains(fn ($m) => ! PermissionMatrix::within($m->site_id, $m->environment, null, $input['scope']))) {
            throw ValidationException::withMessages(['owners' => 'One or more owners are unavailable in this scope.']);
        }
        $owners = $input['owners'];
        sort($owners, SORT_STRING);

        return response()->json(['allowed' => true, 'tenant_id' => $tenant, 'owners' => $owners]);
    }
}
