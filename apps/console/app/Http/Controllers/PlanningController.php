<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Application\Inventory\Contracts\InventoryGateway;
use App\Application\Planning\Contracts\ApprovalGateway;
use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Identity\IdentityFailure;
use App\Domain\Planning\PlanningFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

final class PlanningController
{
    public function index(Request $request, string $tenant, string $application, string $environment, CatalogueGateway $catalogue): Response
    {
        $input = $request->validate(['revision' => ['required', 'uuid', 'lowercase']]);
        $revision = $catalogue->call($this->session($request), $tenant, 'getRevision', ['application' => $application, 'revision' => $input['revision']], environment: $environment);
        Inertia::clearHistory();

        return Inertia::render('planning/Workspace', ['tenantId' => $tenant, 'applicationId' => $application, 'environment' => $environment, 'revisionId' => $revision['id'], 'record' => null, 'sites' => [], 'notice' => null]);
    }

    public function destinations(Request $request, string $tenant, string $application, string $environment, string $site, InventoryGateway $inventory): JsonResponse
    {
        return response()->json($inventory->call($this->session($request), $tenant, 'listEndpoints', ['site' => $site]))->header('Cache-Control', 'no-store, private');
    }

    public function show(Request $request, string $tenant, string $application, string $environment, string $kind, string $record, PlanningGateway $planning): Response
    {
        $sites = $this->sites($request);
        $data = $planning->call($this->session($request), $tenant, $application, $environment, 'GET', $kind.'/'.$record, $sites);
        Inertia::clearHistory();

        return Inertia::render('planning/Workspace', ['tenantId' => $tenant, 'applicationId' => $application, 'environment' => $environment,
            'revisionId' => $data['intent']['id'] ?? $data['content']['intent_revision'], 'record' => $data, 'sites' => $sites, 'notice' => $request->session()->get('planning_notice'), 'comparison' => $request->session()->get('planning_diff')]);
    }

    public function status(Request $request, string $tenant, string $application, string $environment, string $kind, string $record, PlanningGateway $planning): JsonResponse
    {
        $data = $planning->call($this->session($request), $tenant, $application, $environment, 'GET', $kind.'/'.$record, $this->sites($request));

        return response()->json(['available' => true, 'validity' => $data['validity'] ?? null])->header('Cache-Control', 'no-store, private');
    }

    public function command(Request $request, string $tenant, string $application, string $environment, PlanningGateway $planning, ApprovalGateway $governance): RedirectResponse
    {
        $input = $request->validate(['operation' => ['required', 'in:assessments,plans,approval,diff'], 'command_key' => ['required', 'uuid', 'lowercase'], 'sites' => ['required', 'array', 'min:1', 'max:3'], 'sites.*' => ['required', 'uuid', 'lowercase'], 'body' => ['required', 'array']]);
        $sites = $input['sites'];
        $base = '/tenants/'.$tenant.'/applications/'.$application.'/environments/'.$environment.'/planning';
        try {
            $op = $input['operation'];
            if ($op === 'approval') {
                $body = validator($input['body'], ['plan_id' => ['required', 'uuid'], 'plan_digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/']])->validate();
                $plan = $planning->call($this->session($request), $tenant, $application, $environment, 'GET', 'plans/'.$body['plan_id'], $sites);
                if (($plan['validity']['current'] ?? false) !== true || ($plan['binding']['digest'] ?? null) !== $body['plan_digest']) {
                    throw new PlanningFailure(409, 'plan_changed_requires_review');
                }
                $approval = $governance->request($this->session($request), $tenant, ['plan_id' => $plan['id'], 'plan_revision' => $plan['binding']['revision'],
                    'plan_digest' => $plan['binding']['digest'], 'expires_at' => gmdate('c', $plan['binding']['valid_until'])], $input['command_key']);

                return redirect($base.'/plans/'.$plan['id'].'?sites='.implode(',', $sites))->with('planning_notice', 'Approval requested: '.$approval['id'].'. Independent review and current admission checks are still required.');
            }
            if ($op === 'diff') {
                $body = validator($input['body'], ['plan_id' => ['required', 'uuid'], 'other_plan_id' => ['required', 'uuid']])->validate();
                $diff = $planning->call($this->session($request), $tenant, $application, $environment, 'POST', 'plans/'.$body['plan_id'].'/diff', $sites, ['other_plan_id' => $body['other_plan_id']]);

                return redirect($base.'/plans/'.$body['plan_id'].'?sites='.implode(',', $sites))->with('planning_diff', $diff);
            }
            $data = $planning->call($this->session($request), $tenant, $application, $environment, 'POST', $op, $sites, $input['body'], $input['command_key']);

            return redirect($base.'/'.$op.'/'.$data['id'].'?sites='.implode(',', $sites));
        } catch (PlanningFailure|IdentityFailure $e) {
            if (in_array($e->status, [401, 403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your planning access changed.');
            }
            throw ValidationException::withMessages(['command' => $e->status === 503 ? 'The result is uncertain. Retry this command unchanged.' : 'This review is held. Refresh, resolve the findings and review the current plan.', 'planning_status' => (string) $e->status]);
        }
    }

    private function session(Request $request): string
    {
        $value = $request->session()->get('identity.token');
        if (! is_string($value)) {
            throw new PlanningFailure(403);
        }

        return $value;
    }

    /** @return list<string> */
    private function sites(Request $request): array
    {
        $raw = $request->query('sites');
        if (! is_string($raw) || strlen($raw) > 110) {
            throw new PlanningFailure(422, 'invalid_scope');
        }
        $sites = explode(',', $raw);
        foreach ($sites as $site) {
            if (! preg_match('/\A[0-9a-f-]{36}\z/', $site)) {
                throw new PlanningFailure(422, 'invalid_scope');
            }
        }

        return $sites;
    }
}
