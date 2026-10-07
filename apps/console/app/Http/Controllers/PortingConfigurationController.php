<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Inventory\Contracts\InventoryGateway;
use App\Domain\Inventory\InventoryFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

final class PortingConfigurationController
{
    public function show(Request $request, string $tenant, string $site, InventoryGateway $inventory): Response
    {
        $data = $inventory->call($this->session($request), $tenant, 'getPortingConfiguration', ['site' => $site]);
        Inertia::clearHistory();

        return Inertia::render('inventory/Configuration', ['tenantId' => $tenant, 'siteId' => $site, 'workspace' => $data, 'notice' => $request->session()->get('inventory_notice')]);
    }

    public function status(Request $request, string $tenant, string $site, InventoryGateway $inventory): JsonResponse
    {
        $inventory->call($this->session($request), $tenant, 'getPortingConfiguration', ['site' => $site]);

        return response()->json(['available' => true])->header('Cache-Control', 'no-store, private');
    }

    public function command(Request $request, string $tenant, string $site, InventoryGateway $inventory): RedirectResponse
    {
        $input = $request->validate(['operation' => ['required', 'in:save,confirm,pull'], 'command_key' => ['required', 'uuid', 'lowercase'], 'revision' => ['nullable', 'integer', 'min:1', 'max:999999999'], 'endpoint_id' => ['nullable', 'uuid', 'lowercase'], 'configuration' => ['required_if:operation,save', 'array:source_endpoint,target_endpoint,manual,choices'], 'configuration.source_endpoint' => ['present_if:operation,save', 'nullable', 'uuid', 'lowercase'], 'configuration.target_endpoint' => ['present_if:operation,save', 'nullable', 'uuid', 'lowercase'], 'configuration.manual' => ['sometimes', 'array', 'max:13'], 'configuration.choices' => ['sometimes', 'array', 'max:20'], 'configuration.choices.*' => ['array'], 'digest' => ['nullable', 'regex:/\A[0-9a-f]{64}\z/']]);
        $parameters = ['site' => $site];
        $operation = match ($input['operation']) {
            'save' => 'savePortingConfiguration',
            'confirm' => 'confirmPortingConfiguration',
            'pull' => 'pullPortingConfiguration',
            default => throw ValidationException::withMessages(['command' => 'Select a valid action.']),
        };
        $body = [];
        if ($input['operation'] === 'save') {
            $body = $input['configuration'];
            // An empty JSON object must stay an object across PHP's associative decoding.
            if (isset($body['manual']) && is_array($body['manual'])) {
                $body['manual'] = (object) array_filter($body['manual'], fn ($value) => $value !== '' && $value !== null);
            }
            foreach (array_keys($body['choices'] ?? []) as $index) {
                $choice = &$body['choices'][$index];
                if (($choice['reason'] ?? null) === null) {
                    $choice['reason'] = '';
                }
            }
            unset($choice);
        } elseif ($input['operation'] === 'confirm') {
            $body = ['digest' => $input['digest'] ?? null];
        } else {
            if (! is_string($input['endpoint_id'] ?? null)) {
                throw ValidationException::withMessages(['command' => 'Select an enrolled endpoint to pull.']);
            }
            $parameters['endpoint'] = $input['endpoint_id'];
        }
        try {
            // Pulls need both administration of this review and current collection authority.
            if ($input['operation'] === 'pull') {
                $inventory->call($this->session($request), $tenant, 'getPortingConfiguration', ['site' => $site]);
            }
            $inventory->call($this->session($request), $tenant, $operation, $parameters, $body, $input['command_key'], isset($input['revision']) ? (int) $input['revision'] : null);
        } catch (InventoryFailure $error) {
            if (in_array($error->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your inventory access changed.');
            }
            throw ValidationException::withMessages(['command' => match ($error->status) {
                412 => 'The configuration changed. Refresh, review and save its current revision.',
                503 => 'The result is uncertain. Retry this exact command unchanged.',
                default => 'Review held: '.str_replace('_', ' ', $error->reason).'.',
            }, 'inventory_status' => (string) $error->status]);
        }

        return redirect('/tenants/'.$tenant.'/inventory/sites/'.$site.'/configuration')->with('inventory_notice', match ($input['operation']) {
            'pull' => 'API collection queued. Refresh after collection completes, then save the findings for review.',
            'confirm' => 'Configuration review confirmed. Native qualification remains separate.',
            default => 'Revision saved. Review the API findings, overrides and gaps before confirming.',
        });
    }

    private function session(Request $request): string
    {
        $token = $request->session()->get('identity.token');
        if (! is_string($token)) {
            throw new InventoryFailure(403, 'access_unavailable');
        }

        return $token;
    }
}
