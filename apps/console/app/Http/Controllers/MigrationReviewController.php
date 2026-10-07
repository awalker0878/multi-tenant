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

final class MigrationReviewController
{
    public function show(Request $request, string $tenant, string $site, InventoryGateway $inventory): Response
    {
        $workspace = $inventory->call($this->session($request), $tenant, 'getMigrationReview', ['site' => $site]);
        Inertia::clearHistory();

        return Inertia::render('inventory/Migration', ['tenantId' => $tenant, 'siteId' => $site, 'workspace' => $workspace, 'notice' => $request->session()->get('inventory_notice')]);
    }

    public function status(Request $request, string $tenant, string $site, InventoryGateway $inventory): JsonResponse
    {
        $inventory->call($this->session($request), $tenant, 'getMigrationReview', ['site' => $site]);

        return response()->json(['available' => true])->header('Cache-Control', 'no-store, private');
    }

    public function command(Request $request, string $tenant, string $site, InventoryGateway $inventory): RedirectResponse
    {
        $input = $request->validate([
            'operation' => ['required', 'in:save,confirm'], 'command_key' => ['required', 'uuid', 'lowercase'],
            'revision' => ['nullable', 'integer', 'min:1', 'max:999999999'],
            'review' => ['required_if:operation,save', 'array:source_profile_id,target_profile_id,method,datasets,owner_inputs,objectives,overrides'],
            'review.source_profile_id' => ['required_if:operation,save', 'uuid', 'lowercase'],
            'review.target_profile_id' => ['required_if:operation,save', 'uuid', 'lowercase'],
            'review.method' => ['required_if:operation,save', 'string', 'max:80'],
            'review.datasets' => ['required_if:operation,save', 'array', 'min:1', 'max:256'],
            'review.owner_inputs' => ['required_if:operation,save', 'array', 'size:8'],
            'review.objectives' => ['required_if:operation,save', 'array'],
            'review.overrides' => ['present_if:operation,save', 'array', 'max:8'],
            'digest' => ['required_if:operation,confirm', 'nullable', 'regex:/\A[0-9a-f]{64}\z/'],
        ]);
        try {
            $inventory->call($this->session($request), $tenant,
                $input['operation'] === 'save' ? 'saveMigrationReview' : 'confirmMigrationReview',
                ['site' => $site], $input['operation'] === 'save' ? $input['review'] : ['digest' => $input['digest']],
                $input['command_key'], isset($input['revision']) ? (int) $input['revision'] : null);
        } catch (InventoryFailure $error) {
            if (in_array($error->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your inventory access changed.');
            }
            throw ValidationException::withMessages(['command' => match ($error->status) {
                412 => 'The review changed. Refresh and review the current revision.',
                503 => 'The result is uncertain. Retry this exact command unchanged.',
                default => 'Review held: '.str_replace('_', ' ', $error->reason).'.',
            }, 'inventory_status' => (string) $error->status]);
        }

        return redirect('/tenants/'.$tenant.'/inventory/sites/'.$site.'/migration')->with('inventory_notice',
            $input['operation'] === 'save' ? 'Migration review saved. Check all disks and owner inputs before confirming.' : 'This migration review is confirmed. Execution requires current approval and qualification.');
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
