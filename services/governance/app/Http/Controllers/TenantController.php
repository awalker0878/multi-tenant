<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Tenancy\Actions\EvaluateTenantPermission;
use App\Application\Tenancy\Actions\ManageTenant;
use App\Application\Tenancy\Actions\ReadTenant;
use App\Domain\Tenancy\PermissionMatrix;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;

final class TenantController
{
    public function index(Request $request, ReadTenant $read): JsonResponse
    {
        return response()->json($read->handle((string) $request->header('X-Console-Session'), null, 'tenants'));
    }

    public function show(Request $request, string $tenant, ReadTenant $read, string $view = 'tenant'): JsonResponse
    {
        return response()->json($read->handle((string) $request->header('X-Console-Session'), $tenant, $view));
    }

    public function create(Request $request, ManageTenant $manage): JsonResponse
    {
        $input = $request->validate(['name' => ['required', 'string', 'max:200'], 'administrator_subject' => ['required', 'string', 'max:255']]);

        return response()->json($manage->handle((string) $request->header('X-Console-Session'), null, 'create', $this->key($request), $input), 201);
    }

    public function update(Request $request, string $tenant, ManageTenant $manage, string $operation): JsonResponse
    {
        $revision = ['required', 'integer', 'min:0'];
        $nullableScope = ['present', 'nullable', 'string', 'max:64', 'regex:/\A[A-Za-z0-9._:-]+\z/'];
        $input = $request->validate(match ($operation) {
            'state' => ['revision' => $revision, 'state' => ['required', 'in:active,suspended']],
            'membership' => ['revision' => $revision, 'subject' => ['required', 'string', 'max:255'],
                'role' => ['required', Rule::in(array_keys(PermissionMatrix::ROLES))], 'state' => ['required', 'in:active,revoked'],
                'site_id' => $nullableScope, 'environment' => $nullableScope, 'expires_at' => ['present', 'nullable', 'date', 'after:now']],
            'grant' => ['membership_id' => ['required', 'uuid'], 'action' => ['required', Rule::in(PermissionMatrix::DELEGABLE)],
                'site_id' => $nullableScope, 'environment' => $nullableScope, 'resource_id' => ['present', 'nullable', 'string', 'max:128'],
                'expires_at' => ['required', 'date', 'after:now', 'before:'.now()->addDays(30)->toIso8601String()]],
            'revoke_grant' => ['grant_id' => ['required', 'uuid'], 'revision' => $revision, 'reason' => ['required', 'string', 'max:1000']],
            'quota' => ['revision' => $revision, 'entitlement' => ['required', 'array:vcpu,memory_mib,storage_gib,workloads'],
                'entitlement.vcpu' => ['required', 'integer', 'min:0', 'max:1000000000'],
                'entitlement.memory_mib' => ['required', 'integer', 'min:0', 'max:1000000000'],
                'entitlement.storage_gib' => ['required', 'integer', 'min:0', 'max:1000000000'],
                'entitlement.workloads' => ['required', 'integer', 'min:0', 'max:1000000000']],
            default => [],
        });
        if (isset($input['revision'])) {
            $input['revision'] = (int) $input['revision'];
        }

        if ($operation === 'quota') {
            $input['entitlement'] = array_map(static fn ($value): int => (int) $value, $input['entitlement']);
        }

        return response()->json($manage->handle((string) $request->header('X-Console-Session'), $tenant, $operation, $this->key($request), $input));
    }

    public function decision(Request $request, string $tenant, EvaluateTenantPermission $evaluate): JsonResponse
    {
        $input = $request->validate(['action' => ['required', 'string', 'max:64'],
            'scope' => ['present', 'array:site_id,environment,resource_id'],
            'scope.site_id' => ['nullable', 'string', 'max:64'], 'scope.environment' => ['nullable', 'string', 'max:64'],
            'scope.resource_id' => ['nullable', 'string', 'max:128']]);

        return response()->json($evaluate->handle((string) $request->header('X-Console-Session'), $tenant, $input['action'], $input['scope']));
    }

    private function key(Request $request): string
    {
        $key = $request->header('Idempotency-Key');
        if (! is_string($key) || ! preg_match('/\A[A-Za-z0-9_-]{8,128}\z/', $key)) {
            throw ValidationException::withMessages(['idempotency_key' => 'Supply an Idempotency-Key of 8–128 letters, digits, underscores or hyphens.']);
        }

        return $key;
    }
}
