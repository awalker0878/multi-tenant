<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Approvals\Actions\InspectExecution;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

final class ExecutionApprovalController
{
    public function __invoke(Request $request, string $tenant, InspectExecution $inspect): JsonResponse
    {
        return $this->respond($request, $tenant, $inspect, false);
    }

    public function native(Request $request, string $tenant, InspectExecution $inspect): JsonResponse
    {
        return $this->respond($request, $tenant, $inspect, true);
    }

    private function respond(Request $request, string $tenant, InspectExecution $inspect, bool $native): JsonResponse
    {
        abort_unless($request->attributes->get('verified_service') === 'lifecycle', 403);
        abort_if(strlen($request->getContent()) > 16384 || array_diff(array_keys($request->all()), ['actor_id', 'approval_id', 'plan_id', 'plan_revision', 'plan_digest']) !== [], 422);
        $input = $request->validate(['actor_id' => ['required', 'uuid', 'lowercase'], 'approval_id' => ['required', 'uuid', 'lowercase'],
            'plan_id' => ['required', 'uuid', 'lowercase'], 'plan_revision' => ['required', 'integer', 'min:1'],
            'plan_digest' => ['required', 'regex:/\A[0-9a-f]{64}\z/']]);
        $input['plan_revision'] = (int) $input['plan_revision'];

        return response()->json($native ? $inspect->native($tenant, $input) : $inspect->handle($tenant, $input));
    }
}
