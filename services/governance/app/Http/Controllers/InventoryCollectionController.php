<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

final class InventoryCollectionController
{
    public function __invoke(Request $request, string $tenant, AuthorizeTenant $authority): JsonResponse
    {
        if ($request->attributes->get('verified_service') !== 'inventory') {
            throw new IdentityDenied('forbidden', 403);
        }
        if (array_diff(array_keys($request->all()), ['owner_id', 'site_id', 'policy_digest']) !== []) {
            throw ValidationException::withMessages(['request' => 'Unexpected fields.']);
        }
        $input = $request->validate(['owner_id' => ['required', 'uuid', 'lowercase'], 'site_id' => ['required', 'uuid', 'lowercase'], 'policy_digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/']]);
        $actor = DB::table('app.federated_actors as a')->join('app.oidc_connections as c', 'c.issuer', '=', 'a.issuer')
            ->join('app.oidc_installation as i', 'i.active_revision', '=', 'c.revision')
            ->where('i.id', 1)->where('a.id', $input['owner_id'])->whereNull('a.disabled_at')->first(['a.id']);
        if ($actor === null) {
            throw new IdentityDenied('forbidden', 403);
        }
        $authority->handle(new FederatedIdentity($input['owner_id'], false), $tenant, 'inventory.admin', ['site_id' => $input['site_id'], 'environment' => null, 'resource_id' => null]);

        return response()->json(['allowed' => true, 'tenant_id' => $tenant, 'owner_id' => $input['owner_id'], 'site_id' => $input['site_id'], 'policy_digest' => $input['policy_digest'], 'evaluated_at' => now()->toIso8601String(), 'native_write_authorized' => false]);
    }
}
