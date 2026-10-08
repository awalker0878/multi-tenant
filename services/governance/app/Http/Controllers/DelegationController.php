<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Identity\Actions\InspectActorDelegation;
use App\Application\Identity\Actions\IssueActorDelegation;
use App\Application\Identity\Actions\RevokeActorDelegation;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;

final class DelegationController
{
    public function issue(Request $request, string $tenant, IssueActorDelegation $issue): JsonResponse
    {
        $input = $this->input($request, true);

        return response()->json($issue->handle((string) $request->header('X-Console-Session'), $tenant, $input['audience'], $input['action'], $input['scope']), 201);
    }

    public function inspect(Request $request, string $tenant, InspectActorDelegation $inspect): JsonResponse
    {
        $input = $this->input($request, false);
        $tokens = $request->headers->all('x-actor-delegation');
        if (count($tokens) !== 1 || ! is_string($tokens[0])) {
            throw ValidationException::withMessages(['delegation' => 'Supply one actor delegation.']);
        }

        return response()->json($inspect->handle((string) $request->attributes->get('verified_service'), $tokens[0], $tenant, $input['action'], $input['scope']));
    }

    public function revoke(Request $request, string $tenant, string $delegation, RevokeActorDelegation $revoke): JsonResponse
    {
        if ($request->all() !== []) {
            throw ValidationException::withMessages(['request' => 'Unexpected fields.']);
        }
        $revoke->handle((string) $request->header('X-Console-Session'), $tenant, $delegation);

        return response()->json(['revoked' => true]);
    }

    /** @return array<string, mixed> */
    private function input(Request $request, bool $issuing): array
    {
        $keys = $issuing ? ['audience', 'action', 'scope'] : ['action', 'scope'];
        if (array_diff(array_keys($request->all()), $keys) !== []) {
            throw ValidationException::withMessages(['request' => 'Unexpected fields.']);
        }

        return $request->validate([
            ...($issuing ? ['audience' => ['required', 'string', 'in:catalogue,inventory,planning,assurance,lifecycle']] : []),
            'action' => ['required', 'string', 'max:64'], 'scope' => ['required', 'array:site_id,environment,resource_id'],
            'scope.site_id' => ['present', 'nullable', 'string', 'max:64'],
            'scope.environment' => ['present', 'nullable', 'string', 'max:64'],
            'scope.resource_id' => ['present', 'nullable', 'string', 'max:128'],
        ]);
    }
}
