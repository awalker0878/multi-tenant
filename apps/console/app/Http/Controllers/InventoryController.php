<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Application\Inventory\Contracts\InventoryGateway;
use App\Domain\Catalogue\CatalogueFailure;
use App\Domain\Identity\IdentityFailure;
use App\Domain\Inventory\InventoryFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

final class InventoryController
{
    public function index(Request $request, string $tenant, InventoryGateway $inventory): Response
    {
        $data = $inventory->call($this->session($request), $tenant, 'listSites', cursor: $this->cursor($request));
        Inertia::clearHistory();

        return Inertia::render('inventory/Index', ['tenantId' => $tenant, 'sites' => $data]);
    }

    public function site(Request $request, string $tenant, string $site, InventoryGateway $inventory): Response
    {
        $session = $this->session($request);
        $data = $inventory->call($session, $tenant, 'listEndpoints', ['site' => $site], cursor: $this->cursor($request));
        $admin = $inventory->permitted($session, $tenant, 'inventory.admin', $site);
        Inertia::clearHistory();

        return Inertia::render('inventory/Site', ['tenantId' => $tenant, 'siteId' => $site, 'endpoints' => $data,
            'policies' => $admin ? $inventory->call($session, $tenant, 'listPolicies', ['site' => $site])['items'] : [],
            'health' => $inventory->call($session, $tenant, 'siteHealth', ['site' => $site]), 'canAdminister' => $admin,
            'canDiscover' => $inventory->permitted($session, $tenant, 'inventory.discover', $site),
            'notice' => $request->session()->get('inventory_notice')]);
    }

    public function resources(Request $request, string $tenant, string $site, string $generation, InventoryGateway $inventory): Response
    {
        $session = $this->session($request);
        $data = $inventory->call($session, $tenant, 'listResources', ['site' => $site, 'generation' => $generation], cursor: $this->cursor($request));
        Inertia::clearHistory();

        return Inertia::render('inventory/Resources', ['tenantId' => $tenant, 'siteId' => $site, 'resources' => $data,
            'canMatch' => $inventory->permitted($session, $tenant, 'inventory.match', $site), 'notice' => $request->session()->get('inventory_notice')]);
    }

    public function status(Request $request, string $tenant, string $site, InventoryGateway $inventory): JsonResponse
    {
        $inventory->call($this->session($request), $tenant, 'siteHealth', ['site' => $site]);

        return response()->json(['available' => true])->header('Cache-Control', 'no-store, private');
    }

    public function command(Request $request, string $tenant, string $site, InventoryGateway $inventory, CatalogueGateway $catalogue): RedirectResponse
    {
        $input = $request->validate(['operation' => ['required', 'in:enrollEndpoint,requestDiscovery,renewEndpoint,revokeEndpoint,proposeMatch'], 'command_key' => ['required', 'uuid', 'lowercase'],
            'endpoint_id' => ['nullable', 'uuid', 'lowercase'], 'revision' => ['nullable', 'integer', 'min:1', 'max:999999999'], 'policy_id' => ['nullable', 'uuid', 'lowercase'], 'label' => ['nullable', 'string', 'max:120'],
            'resource_id' => ['nullable', 'uuid', 'lowercase'], 'application_id' => ['nullable', 'uuid', 'lowercase'], 'intent_revision' => ['nullable', 'uuid', 'lowercase'], 'generation_id' => ['nullable', 'uuid', 'lowercase'], 'environment' => ['nullable', 'uuid', 'lowercase']]);
        $operation = $input['operation'];
        $parameters = ['site' => $site];
        if ($operation !== 'enrollEndpoint') {
            if (! is_string($input['endpoint_id'] ?? null)) {
                throw ValidationException::withMessages(['command' => 'Select an endpoint.']);
            }
            $parameters['endpoint'] = $input['endpoint_id'];
        }
        $body = match ($operation) {
            'enrollEndpoint' => ['policy_id' => $input['policy_id'] ?? null, 'label' => $input['label'] ?? null],
            'proposeMatch' => ['resource_id' => $input['resource_id'] ?? null, 'application_id' => $input['application_id'] ?? null, 'intent_revision' => $input['intent_revision'] ?? null, 'generation_id' => $input['generation_id'] ?? null],
            default => [],
        };
        try {
            if ($operation === 'proposeMatch') {
                foreach (['application_id', 'intent_revision', 'environment'] as $required) {
                    if (! is_string($input[$required] ?? null)) {
                        throw ValidationException::withMessages(['command' => 'Select the application, intent revision and environment.']);
                    }
                }
                // Confirm access through Catalogue's owner API; no domain database is shared.
                $catalogue->call($this->session($request), $tenant, 'getRevision', ['application' => $input['application_id'], 'revision' => $input['intent_revision']], environment: $input['environment']);
            }
            $inventory->call($this->session($request), $tenant, $operation, $parameters, $body, $input['command_key'], isset($input['revision']) ? (int) $input['revision'] : null);
        } catch (InventoryFailure|IdentityFailure|CatalogueFailure $e) {
            if (in_array($e->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your inventory access changed.');
            }
            $message = match ($e->status) {
                412 => 'This enrollment changed. Refresh and review its current revision.',
                503 => 'The result is uncertain. Retry this exact command unchanged.',
                429 => 'The discovery budget is busy. Retry this command later.',
                default => 'The command is held: '.str_replace('_', ' ', $e instanceof InventoryFailure ? $e->reason : 'authority unavailable').'.',
            };
            throw ValidationException::withMessages(['command' => $message, 'inventory_status' => (string) $e->status]);
        }
        $location = '/tenants/'.$tenant.'/inventory/sites/'.$site;
        if ($operation === 'proposeMatch') {
            $location .= '/generations/'.$input['generation_id'];
        }

        return redirect($location)->with('inventory_notice', $operation === 'proposeMatch' ? 'Matching proposal recorded. Ownership remains unassigned.' : 'Command accepted. Refresh to check collection progress.');
    }

    private function session(Request $request): string
    {
        $value = $request->session()->get('identity.token');
        if (! is_string($value)) {
            throw new InventoryFailure(403, 'access_unavailable');
        }

        return $value;
    }

    private function cursor(Request $request): ?string
    {
        $value = $request->query('cursor');
        if ($value !== null && (! is_string($value) || ! preg_match('/\A[0-9a-f-]{36}\z/', $value))) {
            throw new InventoryFailure(422, 'invalid_cursor');
        }

        return $value;
    }
}
