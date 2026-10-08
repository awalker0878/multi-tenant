<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Jobs\Contracts\JobsGateway;
use App\Domain\Jobs\JobsFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

final class NativeJobController
{
    public function show(Request $request, string $tenant, string $site, string $application, string $environment, string $job, JobsGateway $jobs): Response
    {
        $result = $this->call($request, $jobs, $tenant, $site, $application, $environment, $job);
        Inertia::clearHistory();

        return Inertia::render('jobs/NativeJob', ['tenantId' => $tenant, 'base' => $request->url(), 'initial' => $result]);
    }

    public function status(Request $request, string $tenant, string $site, string $application, string $environment, string $job, JobsGateway $jobs): JsonResponse
    {
        return $this->response($request, $jobs, $tenant, $site, $application, $environment, $job);
    }

    public function command(Request $request, string $tenant, string $site, string $application, string $environment, string $job, JobsGateway $jobs): JsonResponse
    {
        $request->validate(['action' => ['required', 'in:stop,continue-transfer'], 'expected_revision' => ['required', 'integer', 'min:1']]);

        return $this->response($request, $jobs, $tenant, $site, $application, $environment, $job, true);
    }

    private function response(Request $request, JobsGateway $jobs, string $tenant, string $site, string $application, string $environment, string $job, bool $command = false): JsonResponse
    {
        try {
            $result = $this->call($request, $jobs, $tenant, $site, $application, $environment, $job, $command);
            $status = $command ? 202 : 200;
        } catch (JobsFailure $error) {
            $result = ['error' => $error->reason];
            $status = $error->status;
        }

        return response()->json($result, $status)->header('Cache-Control', 'no-store, private');
    }

    /** @return array<string, mixed> */
    private function call(Request $request, JobsGateway $jobs, string $tenant, string $site, string $application, string $environment, string $job, bool $command = false): array
    {
        return $jobs->call((string) $request->session()->get('identity.token'), $tenant,
            ['site_id' => $site, 'environment' => $environment, 'resource_id' => $application],
            $command ? 'POST' : 'GET', 'native-jobs/'.$job.($command ? '/'.$request->string('action')->toString() : ''),
            $command ? ['expected_revision' => (int) $request->input('expected_revision')] : []);
    }
}
