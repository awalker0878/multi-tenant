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

final class OperatorInputsController
{
    public function show(Request $request, string $tenant, string $site, InventoryGateway $inventory): Response
    {
        $workspace = $this->read($request, $tenant, $site, $inventory);
        Inertia::clearHistory();

        return Inertia::render('inventory/OperatorInputs', ['tenantId' => $tenant, 'siteId' => $site, 'workspace' => $workspace, 'notice' => $request->session()->get('inventory_notice')]);
    }

    public function status(Request $request, string $tenant, string $site, InventoryGateway $inventory): JsonResponse
    {
        $this->read($request, $tenant, $site, $inventory);

        return response()->json(['available' => true])->header('Cache-Control', 'no-store, private');
    }

    public function download(Request $request, string $tenant, string $site, InventoryGateway $inventory): JsonResponse
    {
        $workspace = $this->read($request, $tenant, $site, $inventory);
        abort_if($workspace['record'] === null, 404);

        return response()->json(['schema_version' => 1, 'packet_type' => 'operator-input-handoff', 'qualification_status' => 'not_established', ...$workspace], 200, [
            'Content-Disposition' => 'attachment; filename="operator-inputs.json"',
            'Cache-Control' => 'no-store, private',
        ], JSON_PRETTY_PRINT);
    }

    public function save(Request $request, string $tenant, string $site, InventoryGateway $inventory): RedirectResponse
    {
        $input = $request->validate([
            'command_key' => ['required', 'uuid', 'lowercase'],
            'revision' => ['nullable', 'integer', 'min:1', 'max:999999999'],
            'input' => ['required', 'array:values,configuration_digest'],
            'input.values' => ['present', 'array', 'max:32'],
            'input.configuration_digest' => ['present', 'nullable', 'regex:/\A[0-9a-f]{64}\z/'],
        ]);
        $body = $input['input'];
        $body['values'] = (object) array_filter($body['values'], fn ($value) => $value !== '' && $value !== null);
        try {
            $inventory->call($this->session($request), $tenant, 'saveOperatorInputs', ['site' => $site], $body, $input['command_key'], isset($input['revision']) ? (int) $input['revision'] : null);
        } catch (InventoryFailure $error) {
            if (in_array($error->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your inventory access changed.');
            }
            throw ValidationException::withMessages(['command' => match (true) {
                $error->status === 412, $error->status === 428 => 'A saved revision or environment review changed. Refresh and review the current record before saving.',
                $error->status === 503 => 'The result is uncertain. Recover the unchanged save before editing further.',
                $error->reason === 'independent_verification_account_required' => 'Verification accounts must use separate references from every execution account.',
                $error->reason === 'invalid_operator_reference' => 'Use a record identifier of up to 240 characters. Do not enter secret values, spaces, query strings or credential bundles.',
                $error->reason === 'invalid_operator_target' => 'Enter whole numbers within the displayed target limits. Zero is valid for outage and data loss.',
                default => 'These inputs could not be saved. Review the field values and try again.',
            }, 'inventory_status' => (string) $error->status]);
        }

        return redirect('/tenants/'.$tenant.'/inventory/sites/'.$site.'/operator-inputs')->with('inventory_notice', 'Operator inputs saved. Remaining requirements are listed below.');
    }

    /** @return array<string,mixed> */
    private function read(Request $request, string $tenant, string $site, InventoryGateway $inventory): array
    {
        $workspace = $inventory->call($this->session($request), $tenant, 'getOperatorInputs', ['site' => $site]);
        if (is_array($workspace['record'] ?? null)) {
            $workspace['record']['values'] = (object) $workspace['record']['values'];
        }

        return $workspace;
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
