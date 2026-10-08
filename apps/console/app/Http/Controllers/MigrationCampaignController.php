<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Jobs\Contracts\JobsGateway;
use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Jobs\JobsFailure;
use App\Domain\Planning\PlanningFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

final class MigrationCampaignController
{
    public function show(Request $request, string $tenant, string $site, string $application, string $environment, JobsGateway $jobs, ?string $campaign = null): Response
    {
        $result = $jobs->call($this->session($request), $tenant, $this->scope($site, $application, $environment), 'GET', 'migration-campaigns'.($campaign === null ? '' : '/'.$campaign));
        Inertia::clearHistory();

        return Inertia::render('jobs/Campaigns', ['tenantId' => $tenant, 'base' => $this->base($tenant, $site, $application, $environment), 'initial' => $result, 'campaignId' => $campaign]);
    }

    public function status(Request $request, string $tenant, string $site, string $application, string $environment, JobsGateway $jobs, ?string $campaign = null): JsonResponse
    {
        try {
            $result = $jobs->call($this->session($request), $tenant, $this->scope($site, $application, $environment), 'GET', 'migration-campaigns'.($campaign === null ? '' : '/'.$campaign));

            return $this->json($result);
        } catch (JobsFailure $e) {
            return $this->json(['error' => $e->reason], $e->status);
        }
    }

    public function plan(Request $request, string $tenant, string $site, string $application, string $environment, string $plan, PlanningGateway $planning): JsonResponse
    {
        try {
            $record = $planning->call($this->session($request), $tenant, $application, $environment, 'GET', 'plans/'.$plan, [$site]);
            $content = $record['content'] ?? [];
            if (($record['validity']['current'] ?? false) !== true || ($content['action'] ?? null) !== 'application.migrate'
                || ($content['execution_ready'] ?? false) !== true || ($record['binding']['lane'] ?? null) !== 'operational'
                || ! is_array($content['migration_campaign'] ?? null) || ($content['scope']['site_id'] ?? null) !== $site) {
                throw new PlanningFailure(423, 'complete_current_migration_plan_required');
            }

            return $this->json(['plan_id' => $record['binding']['plan_id'], 'plan_revision' => $record['binding']['revision'], 'plan_digest' => $record['binding']['digest'], 'method' => $content['migration_campaign']['method'], 'mode' => $content['migration_campaign']['mode']]);
        } catch (PlanningFailure $e) {
            return $this->json(['error' => $e->reason], $e->status);
        }
    }

    public function create(Request $request, string $tenant, string $site, string $application, string $environment, JobsGateway $jobs): JsonResponse
    {
        $input = $request->validate(['command_key' => ['required', 'uuid', 'lowercase'], 'settings' => ['required', 'array'], 'members' => ['required', 'array', 'min:1', 'max:1000']]);
        try {
            $scope = $this->scope($site, $application, $environment);
            $result = $jobs->call($this->session($request), $tenant, $scope, 'POST', 'migration-campaigns', ['scope' => $scope, 'settings' => $input['settings'], 'members' => $input['members']], $input['command_key']);

            return $this->json($result, 202);
        } catch (JobsFailure $e) {
            return $this->json(['error' => $e->reason], $e->status);
        }
    }

    public function command(Request $request, string $tenant, string $site, string $application, string $environment, string $campaign, JobsGateway $jobs): JsonResponse
    {
        $input = $request->validate(['command_key' => ['required', 'uuid', 'lowercase'], 'action' => ['required', 'in:schedule,pause,cancel'], 'expected_revision' => ['required', 'integer', 'min:1']]);
        try {
            $result = $jobs->call($this->session($request), $tenant, $this->scope($site, $application, $environment), 'POST', 'migration-campaigns/'.$campaign.'/commands', ['action' => $input['action'], 'expected_revision' => (int) $input['expected_revision']], $input['command_key']);

            return $this->json($result, 202);
        } catch (JobsFailure $e) {
            return $this->json(['error' => $e->reason], $e->status);
        }
    }

    /** @return array{site_id: string, environment: string, resource_id: string} */
    private function scope(string $site, string $application, string $environment): array
    {
        return ['site_id' => $site, 'environment' => $environment, 'resource_id' => $application];
    }

    private function session(Request $request): string
    {
        return (string) $request->session()->get('identity.token');
    }

    private function base(string $tenant, string $site, string $application, string $environment): string
    {
        return '/tenants/'.$tenant.'/sites/'.$site.'/applications/'.$application.'/environments/'.$environment.'/migration-campaigns';
    }

    /** @param array<string, mixed> $data */
    private function json(array $data, int $status = 200): JsonResponse
    {
        return response()->json($data, $status)->header('Cache-Control', 'no-store, private');
    }
}
