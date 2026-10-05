<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Approvals\Actions\InspectApproval;
use App\Application\Approvals\Actions\ManageApproval;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;

final class ApprovalController
{
    public function request(Request $request, string $tenant, ManageApproval $manage): JsonResponse
    {
        $input = $request->validate(['plan_id' => ['required', 'uuid'], 'plan_revision' => ['required', 'integer', 'min:1'],
            'plan_digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/'], 'expires_at' => ['required', 'date', 'after:now']]);
        $input['plan_revision'] = (int) $input['plan_revision'];

        return response()->json($manage->handle((string) $request->header('X-Console-Session'), $tenant, 'request', $this->key($request), $input), 201);
    }

    public function transition(Request $request, string $tenant, string $approval, ManageApproval $manage, string $operation): JsonResponse
    {
        $input = $request->validate(['revision' => ['required', 'integer', 'min:1'], 'reason' => ['required', 'string', 'max:1000']]);
        $input['revision'] = (int) $input['revision'];
        $input['approval_id'] = $approval;

        return response()->json($manage->handle((string) $request->header('X-Console-Session'), $tenant, $operation, $this->key($request), $input));
    }

    public function show(Request $request, string $tenant, string $approval, InspectApproval $inspect): JsonResponse
    {
        return response()->json($inspect->handle((string) $request->header('X-Console-Session'), $tenant, $approval));
    }

    public function validateApproval(Request $request, string $tenant, string $approval, InspectApproval $inspect): JsonResponse
    {
        $input = $request->validate(['plan_id' => ['required', 'uuid'], 'plan_revision' => ['required', 'integer', 'min:1'],
            'plan_digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/'], 'action' => ['required', 'string', 'max:64'],
            'scope' => ['required', 'array:site_id,environment,resource_id'],
            'scope.site_id' => ['required', 'string', 'max:128'], 'scope.environment' => ['required', 'string', 'max:128'], 'scope.resource_id' => ['required', 'string', 'max:128']]);
        $input['plan_revision'] = (int) $input['plan_revision'];

        return response()->json($inspect->handle((string) $request->header('X-Console-Session'), $tenant, $approval, $input));
    }

    private function key(Request $request): string
    {
        $key = $request->header('Idempotency-Key');
        if (! is_string($key) || ! preg_match('/\A[A-Za-z0-9_-]{8,128}\z/', $key)) {
            throw ValidationException::withMessages(['idempotency_key' => 'Supply a valid Idempotency-Key.']);
        }

        return $key;
    }
}
