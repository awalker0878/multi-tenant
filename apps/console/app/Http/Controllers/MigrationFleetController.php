<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Inventory\Contracts\InventoryGateway;
use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Inventory\InventoryFailure;
use App\Domain\Planning\PlanningFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

final class MigrationFleetController
{
    public function show(Request $request, string $tenant, string $site, InventoryGateway $inventory, ?string $group = null): Response
    {
        $session = $this->session($request);
        $workspace = $inventory->call($session, $tenant, 'getMigrationFleet', ['site' => $site]);
        $detail = $group === null ? null : $inventory->call($session, $tenant, 'getMigrationGroup', ['site' => $site, 'group' => $group]);
        $endpoints = $inventory->call($session, $tenant, 'listEndpoints', ['site' => $site]);
        Inertia::clearHistory();

        return Inertia::render('inventory/Fleet', ['tenantId' => $tenant, 'siteId' => $site, 'workspace' => $workspace, 'detail' => $detail, 'endpoints' => $endpoints, 'notice' => $request->session()->get('inventory_notice')]);
    }

    public function page(Request $request, string $tenant, string $site, InventoryGateway $inventory): JsonResponse
    {
        $input = $request->validate(['cursor' => ['required', 'uuid', 'lowercase']]);

        return response()->json($inventory->call($this->session($request), $tenant, 'getMigrationFleet', ['site' => $site], cursor: $input['cursor']))->header('Cache-Control', 'no-store, private');
    }

    public function status(Request $request, string $tenant, string $site, InventoryGateway $inventory): JsonResponse
    {
        if (! $inventory->permitted($this->session($request), $tenant, 'inventory.admin', $site)) {
            throw new InventoryFailure(403, 'access_unavailable');
        }

        return response()->json(['available' => true])->header('Cache-Control', 'no-store, private');
    }

    public function refresh(Request $request, string $tenant, string $site, InventoryGateway $inventory): RedirectResponse
    {
        $input = $request->validate(['endpoint_id' => ['required', 'uuid', 'lowercase'], 'command_key' => ['required', 'uuid', 'lowercase']]);
        try {
            $inventory->call($this->session($request), $tenant, 'requestDiscovery', ['site' => $site, 'endpoint' => $input['endpoint_id']], [], $input['command_key']);
        } catch (InventoryFailure $error) {
            $this->failure($error);
        }

        return redirect($this->base($tenant, $site))->with('inventory_notice', 'API discovery queued. Refresh the list when collection completes.');
    }

    public function save(Request $request, string $tenant, string $site, InventoryGateway $inventory, ?string $group = null): RedirectResponse
    {
        $input = $request->validate([
            'command_key' => ['required', 'uuid', 'lowercase'], 'revision' => ['nullable', 'integer', 'min:1', 'max:999999999'],
            'selection' => ['required', 'array:name,application_id,environment_id,target_profile_id,format,resource_ids'],
            'selection.name' => ['required', 'string', 'max:120'],
            'selection.application_id' => ['required', 'uuid', 'lowercase'], 'selection.environment_id' => ['required', 'uuid', 'lowercase'],
            'selection.target_profile_id' => ['required', 'uuid', 'lowercase'], 'selection.format' => ['required', 'in:raw,qcow2'],
            'selection.resource_ids' => ['required', 'array', 'min:1', 'max:50'], 'selection.resource_ids.*' => ['required', 'uuid', 'lowercase', 'distinct'],
        ]);
        try {
            $saved = $inventory->call($this->session($request), $tenant, $group === null ? 'createMigrationGroup' : 'updateMigrationGroup', ['site' => $site, ...($group === null ? [] : ['group' => $group])], $input['selection'], $input['command_key'], isset($input['revision']) ? (int) $input['revision'] : null);
        } catch (InventoryFailure $error) {
            $this->failure($error);
        }

        return redirect($this->base($tenant, $site).'/groups/'.$saved['id'])->with('inventory_notice', 'Migration group saved. Review each VM, then prepare the group for the selected destination.');
    }

    public function prepare(Request $request, string $tenant, string $site, string $group, InventoryGateway $inventory, PlanningGateway $planning): JsonResponse
    {
        $input = $request->validate([
            'revision' => ['required', 'integer', 'min:1'], 'digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/'], 'resource_id' => ['required', 'uuid', 'lowercase'],
            'operation' => ['sometimes', 'in:prepare,options,compose'],
            'base_plan_id' => ['required_if:operation,compose', 'uuid', 'lowercase'],
            'recipe_id' => ['required_if:operation,compose', 'uuid', 'lowercase'],
            'command_key' => ['required_if:operation,compose', 'uuid', 'lowercase'],
        ]);
        try {
            $session = $this->session($request);
            $detail = $inventory->call($session, $tenant, 'getMigrationGroup', ['site' => $site, 'group' => $group]);
            if ($detail['group']['revision'] !== (int) $input['revision'] || $detail['group']['digest'] !== $input['digest']) {
                return response()->json(['error' => 'stale_group'], 412)->header('Cache-Control', 'no-store, private');
            }
            $member = null;
            /** @var list<array<string, mixed>> $members */
            $members = $detail['members'];
            foreach ($members as $candidate) {
                if ($candidate['candidate']['resource_id'] === $input['resource_id']) {
                    $member = $candidate;
                    break;
                }
            }
            if ($member === null) {
                return response()->json(['error' => 'member_not_found'], 404)->header('Cache-Control', 'no-store, private');
            }
            if ($member['holds'] !== [] || $member['preparation'] === null) {
                return response()->json(['error' => 'migration_member_held', 'holds' => $member['holds']], 409)->header('Cache-Control', 'no-store, private');
            }
            $selection = $detail['group']['input'];
            $operation = $input['operation'] ?? 'prepare';
            $result = $operation === 'compose'
                ? $planning->call($session, $tenant, $selection['application_id'], $selection['environment_id'], 'POST', 'migration-plans', [$site], $member['preparation'] + ['base_plan_id' => $input['base_plan_id'], 'recipe_id' => $input['recipe_id']], $input['command_key'])
                : $planning->call($session, $tenant, $selection['application_id'], $selection['environment_id'], 'POST', $operation === 'options' ? 'migration-plan-options' : 'migration-preparations', [$site], $member['preparation']);

            return response()->json($result)->header('Cache-Control', 'no-store, private');
        } catch (InventoryFailure|PlanningFailure $error) {
            return response()->json(['error' => $error->reason], $error->status)->header('Cache-Control', 'no-store, private');
        }
    }

    private function failure(InventoryFailure $error): never
    {
        throw ValidationException::withMessages(['command' => match ($error->status) {
            412 => 'This group changed. Refresh before saving.',
            503 => 'The result is uncertain. Retry this exact command unchanged.',
            default => 'Request held: '.str_replace('_', ' ', $error->reason).'.',
        }, 'inventory_status' => (string) $error->status]);
    }

    private function session(Request $request): string
    {
        $token = $request->session()->get('identity.token');
        if (! is_string($token)) {
            throw new InventoryFailure(403, 'access_unavailable');
        }

        return $token;
    }

    private function base(string $tenant, string $site): string
    {
        return '/tenants/'.$tenant.'/inventory/sites/'.$site.'/migration-fleet';
    }
}
