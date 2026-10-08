<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Jobs\Contracts\JobsGateway;
use App\Domain\Jobs\JobsFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

final class JobsController
{
    public function create(Request $request, string $tenant, string $site, string $application, string $environment): Response
    {
        $input = $request->validate(['plan' => ['required', 'uuid', 'lowercase'], 'digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/']]);
        Inertia::clearHistory();

        return Inertia::render('jobs/Admit', ['tenantId' => $tenant, 'base' => $this->base($tenant, $site, $application, $environment), 'planId' => $input['plan'], 'digest' => $input['digest']]);
    }

    public function show(Request $request, string $tenant, string $site, string $application, string $environment, string $job, JobsGateway $jobs): Response
    {
        $result = $jobs->call($this->session($request), $tenant, $this->scope($site, $application, $environment), 'GET', 'jobs/'.$job);
        Inertia::clearHistory();

        return Inertia::render('jobs/Timeline', ['tenantId' => $tenant, 'base' => $this->base($tenant, $site, $application, $environment), 'job' => $result]);
    }

    public function evidence(Request $request, string $tenant, string $site, string $application, string $environment, string $job, string $evidence, JobsGateway $jobs): Response
    {
        $scope = $this->scope($site, $application, $environment);
        $current = $jobs->call($this->session($request), $tenant, $scope, 'GET', 'jobs/'.$job);
        abort_unless(($current['evidence']['id'] ?? null) === $evidence, 404);
        $result = $jobs->call($this->session($request), $tenant, $scope, 'GET', 'evidence/'.$evidence);
        abort_unless(($result['job_id'] ?? null) === $job, 404);
        Inertia::clearHistory();

        return Inertia::render('jobs/Evidence', ['tenantId' => $tenant, 'jobUrl' => $this->base($tenant, $site, $application, $environment).'/'.$job, 'evidence' => $result, 'job' => $current]);
    }

    public function evidenceStatus(Request $request, string $tenant, string $site, string $application, string $environment, string $job, string $evidence, JobsGateway $jobs): JsonResponse
    {
        try {
            $scope = $this->scope($site, $application, $environment);
            $result = $jobs->call($this->session($request), $tenant, $scope, 'GET', 'evidence/'.$evidence);
            if (($result['job_id'] ?? null) !== $job) {
                throw new JobsFailure(404, 'not_found');
            }

            return response()->json(['id' => $result['id'], 'digest' => $result['digest']])->header('Cache-Control', 'no-store, private');
        } catch (JobsFailure $e) {
            return response()->json(['error' => $e->reason], $e->status)->header('Cache-Control', 'no-store, private');
        }
    }

    public function status(Request $request, string $tenant, string $site, string $application, string $environment, string $job, JobsGateway $jobs): JsonResponse
    {
        try {
            $result = $jobs->call($this->session($request), $tenant, $this->scope($site, $application, $environment), 'GET', 'jobs/'.$job);

            return response()->json($result)->header('Cache-Control', 'no-store, private');
        } catch (JobsFailure $e) {
            return response()->json(['error' => $e->reason], $e->status)->header('Cache-Control', 'no-store, private');
        }
    }

    public function admit(Request $request, string $tenant, string $site, string $application, string $environment, JobsGateway $jobs): RedirectResponse
    {
        $input = $request->validate(['command_key' => ['required', 'uuid', 'lowercase'], 'plan_id' => ['required', 'uuid', 'lowercase'],
            'plan_digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/'], 'approval_id' => ['required', 'uuid', 'lowercase'], 'campaign_id' => ['required', 'uuid', 'lowercase']]);
        $key = $input['command_key'];
        unset($input['command_key']);
        $input['plan_revision'] = 1;
        try {
            $job = $jobs->call($this->session($request), $tenant, $this->scope($site, $application, $environment), 'POST', 'jobs', $input, $key);

            return redirect($this->base($tenant, $site, $application, $environment).'/'.$job['id']);
        } catch (JobsFailure $e) {
            return back()->withErrors(['command' => $e->reason, 'command_status' => (string) $e->status]);
        }
    }

    public function command(Request $request, string $tenant, string $site, string $application, string $environment, string $job, JobsGateway $jobs): RedirectResponse
    {
        $input = $request->validate(['command_key' => ['required', 'uuid', 'lowercase'], 'action' => ['required', 'in:pause,cancel,stop,reconcile,resume,retry_unstarted'], 'expected_revision' => ['required', 'integer', 'min:1']]);
        try {
            $jobs->call($this->session($request), $tenant, $this->scope($site, $application, $environment), 'POST', 'jobs/'.$job.'/commands',
                ['action' => $input['action'], 'expected_revision' => (int) $input['expected_revision']], $input['command_key']);

            return back();
        } catch (JobsFailure $e) {
            return back()->withErrors(['command' => $e->reason, 'command_status' => (string) $e->status]);
        }
    }

    private function session(Request $request): string
    {
        return (string) $request->session()->get('identity.token');
    }

    /** @return array{site_id: string, environment: string, resource_id: string} */
    private function scope(string $site, string $application, string $environment): array
    {
        return ['site_id' => $site, 'environment' => $environment, 'resource_id' => $application];
    }

    private function base(string $tenant, string $site, string $application, string $environment): string
    {
        return '/tenants/'.$tenant.'/sites/'.$site.'/applications/'.$application.'/environments/'.$environment.'/jobs';
    }
}
