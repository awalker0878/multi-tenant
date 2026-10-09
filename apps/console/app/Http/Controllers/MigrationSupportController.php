<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Planning\PlanningFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
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

    public function flowChoices(Request $request, string $tenant, string $application, string $environment, string $site, PlanningGateway $planning): JsonResponse
    {
        $choices = $planning->call($this->session($request), $tenant, $application, $environment,
            'POST', 'migration-flow-choices', [$site], ['site_id' => $site]);
        return response()->json(['available' => true, 'flow_choices' => $choices])->header('Cache-Control', 'no-store, private');
    }

    public function saveFlows(Request $request, string $tenant, string $application, string $environment, string $site, PlanningGateway $planning): RedirectResponse
    {
        $input = $request->validate([
            'command_key' => ['required', 'uuid', 'lowercase'],
            'revision' => ['required', 'integer', 'min:0', 'max:1000000'],
            'context_sha256' => ['required', 'regex:/\\A[a-f0-9]{64}\\z/'],
            'selections' => ['present', 'array', 'max:512'],
            'selections.*' => ['required', 'array:source_flow_id,rule_native_ref,route_native_ref'],
            'selections.*.source_flow_id' => ['required', 'regex:/\\A[a-f0-9]{64}\\z/'],
            'selections.*.rule_native_ref' => ['required', 'string', 'max:512'],
            'selections.*.route_native_ref' => ['required', 'string', 'max:512'],
            'omissions' => ['present', 'array', 'max:512'],
            'omissions.*' => ['required', 'array:source_flow_id,reason_code'],
            'omissions.*.source_flow_id' => ['required', 'regex:/\\A[a-f0-9]{64}\\z/'],
            'omissions.*.reason_code' => ['required', 'in:retired_dependency,not_required_at_destination,replaced_by_native_service,accepted_service_limitation'],
        ]);
        try {
            $response = $planning->call(
                $this->session($request), $tenant, $application, $environment,
                'POST', 'migration-flow-selections', [$site], [
                    'site_id' => $site,
                    'revision' => (int) $input['revision'],
                    'context_sha256' => $input['context_sha256'],
                    'selections' => $input['selections'],
                    'omissions' => $input['omissions'],
                ], $input['command_key'],
            );
        } catch (PlanningFailure $error) {
            if (in_array($error->status, [401, 403, 404], true)) {
                throw $error;
            }
            throw ValidationException::withMessages([
                'flow_mapping' => in_array($error->status, [409, 412, 423], true)
                    ? 'Native application flow evidence or revision changed. Refresh choices before saving.'
                    : 'Application flow validation unavailable. No approval was recorded.',
            ]);
        }
        return redirect()->back()->with('flow_notice', ($response['status'] ?? '') === 'eligible'
            ? 'Application flow choices saved for review. Execution still requires fresh independent E4 evidence.'
            : 'Application flow draft saved. Required connectivity or isolation evidence remains held.');
    }

    private function session(Request $request): string
    {
        $token = $request->session()->get('identity.token');
        if (! is_string($token)) {
            throw new PlanningFailure(403, 'access_unavailable');
        }
        return $token;
    }

    /** @return array<string, mixed> */
    private function read(Request $request, string $tenant, string $application, string $environment, string $site, PlanningGateway $planning): array
    {
        return $planning->call($this->session($request), $tenant, $application, $environment, 'POST', 'migration-support', [$site], ['site_id' => $site]);
    }
}
