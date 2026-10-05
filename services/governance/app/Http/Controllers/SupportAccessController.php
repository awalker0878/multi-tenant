<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Support\Actions\DecideSupportAccess;
use App\Application\Support\Actions\ManageSupportSecurity;
use App\Application\Support\Actions\ReadSupportAccess;
use App\Application\Support\Actions\RequestSupportAccess;
use App\Application\Support\Actions\UseSupportAccess;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportPolicy;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;

final class SupportAccessController
{
    private const NAME = 'regex:/\A[A-Za-z0-9][A-Za-z0-9._:-]{0,63}\z/';

    private const REFERENCE = 'regex:/\A[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\z/';

    private const TIMESTAMP = 'regex:/\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\z/';

    public function request(Request $request, string $tenant, RequestSupportAccess $action): JsonResponse
    {
        $input = $this->input($request, ['executor_id' => ['required', 'uuid', 'lowercase'],
            'site_id' => ['required', 'string', self::NAME], 'environment' => ['required', 'string', self::NAME],
            'resources' => ['required', 'array', 'list', 'min:1', 'max:20'],
            'resources.*' => ['required', 'array:kind,id'], 'resources.*.kind' => ['required', Rule::in(['membership', 'grant'])],
            'resources.*.id' => ['required', 'uuid', 'lowercase', 'distinct:strict'],
            'actions' => ['required', 'array', 'list', 'min:1', 'max:2'],
            'actions.*' => ['required', 'string', 'distinct:strict', Rule::in(array_keys(SupportPolicy::ACTIONS))],
            'expires_at' => ['required', 'string', 'date', self::TIMESTAMP], 'reason_code' => ['required', Rule::in(['incident_diagnosis', 'access_investigation'])],
            'case_reference' => ['required', 'string', self::REFERENCE]]);

        return response()->json($action->handle($this->token($request), (string) $request->bearerToken(), $tenant, $this->key($request), $input), 201);
    }

    public function security(Request $request, string $operation, ManageSupportSecurity $action): JsonResponse
    {
        $rules = ['tenant_id' => ['required', 'uuid', 'lowercase'], 'case_reference' => ['required', 'string', self::REFERENCE]];
        $rules += $operation === 'grant' ? ['actor_id' => ['required', 'uuid', 'lowercase'], 'role' => ['required', Rule::in(['approver', 'reviewer'])],
            'site_id' => ['required', 'string', self::NAME], 'environment' => ['required', 'string', self::NAME], 'expires_at' => ['required', 'string', 'date', self::TIMESTAMP]]
            : ['grant_id' => ['required', 'uuid', 'lowercase'], 'revision' => ['required', 'integer', 'min:1'],
                'reason_code' => ['required', Rule::in(['incident_resolved', 'access_no_longer_needed', 'suspected_compromise', 'policy_review'])]];

        return response()->json($action->handle($this->token($request), (string) $request->bearerToken(), $operation, $this->key($request), $this->input($request, $rules)), $operation === 'grant' ? 201 : 200);
    }

    public function decide(Request $request, string $tenant, string $support, string $operation, DecideSupportAccess $action): JsonResponse
    {
        $rules = $this->decision();
        if ($operation === 'review') {
            $rules += ['outcome' => ['required', Rule::in(['acceptable', 'incident'])], 'case_reference' => ['required', 'string', self::REFERENCE]];
        } else {
            $rules += ['role' => [$operation === 'revoke' ? 'sometimes' : 'required', Rule::in(['tenant', 'security'])]];
            if ($operation !== 'approve') {
                $rules += ['reason_code' => ['required', Rule::in(['request_rejected', 'incident_resolved', 'access_no_longer_needed', 'suspected_compromise', 'policy_review'])],
                    'case_reference' => ['required', 'string', self::REFERENCE]];
            }
        }

        return response()->json($action->handle($this->token($request), (string) $request->bearerToken(), $tenant, $support, $operation, $this->key($request), $this->input($request, $rules)));
    }

    public function use(Request $request, string $tenant, string $support, string $operation, UseSupportAccess $action): JsonResponse
    {
        $rules = $operation === 'activate' ? $this->decision() : ['binding_sha256' => ['required', 'regex:/\A[0-9a-f]{64}\z/'],
            'action' => ['required', Rule::in(array_keys(SupportPolicy::ACTIONS))], 'resource_id' => ['required', 'uuid', 'lowercase'],
            'site_id' => ['required', 'string', self::NAME], 'environment' => ['required', 'string', self::NAME]];

        return response()->json($action->handle($this->token($request), (string) $request->bearerToken(), $tenant, $support, $operation,
            $operation === 'activate' ? $this->key($request) : '', $this->input($request, $rules)));
    }

    public function show(Request $request, string $tenant, string $support, ReadSupportAccess $action, bool $history = false): JsonResponse
    {
        $input = $this->input($request, $history ? ['before' => ['sometimes', 'uuid', 'lowercase']] : []);

        return response()->json($action->handle($this->token($request), (string) $request->bearerToken(), $tenant, $support, $history, $input['before'] ?? null));
    }

    /** @return array<string, list<mixed>> */
    private function decision(): array
    {
        return ['revision' => ['required', 'integer', 'min:1'], 'binding_sha256' => ['required', 'regex:/\A[0-9a-f]{64}\z/']];
    }

    /** @param array<string, list<mixed>> $rules
     * @return array<string, mixed>
     */
    private function input(Request $request, array $rules): array
    {
        foreach (['tenant', 'support'] as $parameter) {
            $value = $request->route($parameter);
            if (is_string($value) && $value !== strtolower($value)) {
                throw new IdentityDenied('not_found', 404);
            }
        }
        $allowed = array_filter(array_keys($rules), static fn (string $key): bool => ! str_contains($key, '.'));
        if (array_diff(array_keys($request->all()), $allowed) !== []) {
            throw ValidationException::withMessages(['input' => 'Unexpected input fields.']);
        }
        $input = Validator::make($request->all(), $rules)->validate();
        if (array_key_exists('revision', $input)) {
            $input['revision'] = (int) $input['revision'];
        }

        return $input;
    }

    private function token(Request $request): string
    {
        $headers = $request->headers->all('x-console-session');
        if (count($headers) !== 1 || ! is_string($headers[0]) || ! preg_match('/\A[0-9a-f]{64}\z/', $headers[0])) {
            throw new IdentityDenied('invalid_session');
        }

        return $headers[0];
    }

    private function key(Request $request): string
    {
        $headers = $request->headers->all('idempotency-key');
        if (count($headers) !== 1 || ! is_string($headers[0]) || ! preg_match('/\A[A-Za-z0-9_-]{8,128}\z/', $headers[0])) {
            throw ValidationException::withMessages(['idempotency_key' => 'Supply a valid Idempotency-Key.']);
        }

        return $headers[0];
    }
}
