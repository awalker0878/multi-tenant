<?php

declare(strict_types=1);

namespace App\Infrastructure\Evidence;

use App\Application\Evidence\Contracts\EvidenceAuthority;
use App\Infrastructure\Foundation\MountedSecret;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Http;
use Symfony\Component\HttpKernel\Exception\HttpException;
use Throwable;

final class EvidenceOwners implements EvidenceAuthority
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function producer(array $headers): void
    {
        $this->authenticate($headers, 'producer');
    }

    public function binding(string $tenant, string $job): array
    {
        $binding = $this->request('lifecycle', 'GET', '/internal/evidence-bindings/'.$tenant.'/'.$job);
        abort_unless(($binding['tenant_id'] ?? null) === $tenant
            && ($binding['job_id'] ?? null) === $job
            && ($binding['evidence_level'] ?? null) === 'E2'
            && is_string($binding['digest'] ?? null)
            && preg_match('/\\A[0-9a-f]{64}\\z/', $binding['digest']) === 1
            && is_array($binding['observations'] ?? null),
            503, 'lifecycle_binding_contract_invalid');

        return $binding;
    }

    public function observe(array $observation): void
    {
        $result = $this->request('simulator', 'POST', '/v1/observations', array_intersect_key($observation,
            array_flip(['tenant_id', 'job_id', 'operation_id', 'attempt_id', 'plan_digest', 'epoch', 'simulation'])));
        foreach (array_diff(array_keys($observation), ['observed_at']) as $key) {
            abort_unless(($result[$key] ?? null) === $observation[$key], 409, 'independent_observation_mismatch');
        }
        abort_unless(is_int($result['observed_at'] ?? null) && abs(time() - $result['observed_at']) <= 5, 503);
    }

    public function reader(array $headers, string $tenant, array $scope, string $action): array
    {
        $this->authenticate($headers, 'console');
        $tokens = $headers['x-actor-delegation'] ?? [];
        abort_unless(count($tokens) === 1 && is_string($tokens[0]) && preg_match('/\A[0-9a-f]{64}\z/', $tokens[0]), 403);
        $scope = array_intersect_key($scope, array_flip(['site_id', 'environment', 'resource_id']));
        $result = $this->request('governance', 'POST', '/v1/tenants/'.$tenant.'/delegated-authorizations', ['action' => $action, 'scope' => $scope], $tokens[0]);
        $returnedScope = $result['scope'] ?? null;
        if (is_array($returnedScope)) {
            ksort($returnedScope, SORT_STRING);
        }
        ksort($scope, SORT_STRING);
        $fields = array_keys($result);
        $required = ['allowed', 'delegation_id', 'actor_id', 'delegating_service',
            'audience', 'tenant_id', 'action', 'scope', 'expires_at',
            'evaluated_at', 'authority_use'];
        sort($fields, SORT_STRING);
        sort($required, SORT_STRING);
        abort_unless($fields === $required
            && ($result['delegating_service'] ?? null) === 'console'
            && preg_match('/\\A[0-9a-f-]{36}\\z/', (string) ($result['delegation_id'] ?? '')) === 1
            && preg_match('/\\A[0-9a-f-]{36}\\z/', (string) ($result['actor_id'] ?? '')) === 1,
            503, 'governance_delegation_contract_invalid');
        abort_unless(($result['allowed'] ?? null) === true && ($result['audience'] ?? null) === 'assurance'
            && ($result['tenant_id'] ?? null) === $tenant && ($result['action'] ?? null) === $action && $returnedScope === $scope
            && ($result['authority_use'] ?? null) === 'request_bound' && Carbon::parse($result['expires_at'])->isFuture()
            && Carbon::parse($result['expires_at'])->lessThanOrEqualTo(now()->addSeconds(65))
            && abs(Carbon::parse($result['evaluated_at'])->diffInSeconds(now())) <= 5, 403);

        return $result;
    }

    /** @param array<string, list<string|null>> $headers */
    private function authenticate(array $headers, string $kind): void
    {
        $expected = $this->secrets->read(config('evidence.'.$kind.'_file'));
        abort_unless($expected !== null, 503);
        foreach (['producer', 'console', 'governance', 'lifecycle', 'simulator'] as $other) {
            if ($other !== $kind) {
                abort_if($expected === $this->secrets->read(config('evidence.'.$other.'_file')), 503);
            }
        }
        $values = $headers['authorization'] ?? [];
        abort_unless(count($values) === 1 && is_string($values[0]) && hash_equals('Bearer '.$expected, $values[0]), 403);
    }

    /** @param array<string, mixed>|null $body
     * @return array<string, mixed> */
    private function request(string $owner, string $method, string $path, ?array $body = null, ?string $delegation = null): array
    {
        // Only the three commissioned owner operations are admissible. An
        // arbitrary caller-supplied path can never bypass a published boundary.
        $operations = [
            'lifecycle' => ['GET', '#\\A/internal/evidence-bindings/[0-9a-f-]{36}/[0-9a-f-]{36}\\z#D'],
            'governance' => ['POST', '#\\A/v1/tenants/[0-9a-f-]{36}/delegated-authorizations\\z#D'],
            'simulator' => ['POST', '#\\A/v1/observations\\z#D'],
        ];
        abort_unless(isset($operations[$owner])
            && $operations[$owner][0] === $method
            && preg_match($operations[$owner][1], $path) === 1,
            503, 'owner_operation_uncontracted');
        $base = config('evidence.'.$owner.'_url');
        $url = is_string($base) ? parse_url($base) : false;
        $ca = config('evidence.'.$owner.'_ca');
        $credential = $this->secrets->read(config('evidence.'.$owner.'_file'));
        abort_unless(is_array($url) && ($url['scheme'] ?? null) === 'https' && isset($url['host'])
            && ! isset($url['user']) && ! isset($url['pass']) && ! isset($url['query']) && ! isset($url['fragment'])
            && ($url['path'] ?? '') === '' && is_string($ca) && str_starts_with($ca, '/') && is_readable($ca) && $credential !== null, 503);
        try {
            $headers = $delegation === null ? [] : ['X-Actor-Delegation' => $delegation];
            if ($owner === 'simulator') {
                abort_unless($body !== null && $path === '/v1/observations', 503);
                $encoded = json_encode(self::canonicalize(['path' => $path, 'body' => $body]),
                    JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
                $headers['Idempotency-Key'] = hash('sha256', $encoded);
            }
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeaders($headers)
                ->connectTimeout(2)->timeout(5)->withOptions(['allow_redirects' => false, 'verify' => $ca, 'stream' => true])
                ->send($method, $base.$path, $body === null ? [] : ['json' => $body]);
            $stream = $response->toPsrResponse()->getBody();
            $raw = '';
            try {
                while (! $stream->eof() && strlen($raw) <= 262144) {
                    $raw .= $stream->read(min(65536, 262145 - strlen($raw)));
                }
            } finally {
                $stream->close();
            }
            abort_unless($response->status() === 200 && strlen($raw) <= 262144, 503);
            $result = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
            abort_unless(is_array($result) && ! array_is_list($result), 503);
            if ($owner === 'simulator') {
                $required = ['tenant_id', 'job_id', 'operation_id', 'attempt_id',
                    'plan_digest', 'epoch', 'simulation', 'sealed', 'effect_count',
                    'observed_at', 'outcome'];
                $present = array_keys($result);
                sort($required, SORT_STRING);
                sort($present, SORT_STRING);
                abort_unless($present === $required, 503, 'simulation_receipt_contract_invalid');
                foreach (['tenant_id', 'job_id', 'operation_id', 'attempt_id',
                    'plan_digest', 'epoch', 'simulation'] as $field) {
                    abort_unless(($result[$field] ?? null) === ($body[$field] ?? null),
                        503, 'simulation_receipt_scope_mismatch');
                }
                abort_unless(($result['sealed'] ?? null) === true
                    && is_int($result['effect_count'] ?? null)
                    && $result['effect_count'] >= 0
                    && is_int($result['observed_at'] ?? null)
                    && in_array($result['outcome'] ?? null,
                        ['confirmed_succeeded', 'confirmed_failed'], true),
                    503, 'simulation_receipt_contract_invalid');
            }

            return $result;
        } catch (HttpException $e) {
            throw $e;
        } catch (Throwable) {
            abort(503, 'evidence_owner_unavailable');
        }
    }
    /** @return mixed */
    private static function canonicalize(mixed $value): mixed
    {
        if (! is_array($value)) {
            return $value;
        }
        if (array_is_list($value)) {
            return array_map(self::canonicalize(...), $value);
        }
        ksort($value, SORT_STRING);
        foreach ($value as $key => $child) {
            $value[$key] = self::canonicalize($child);
        }

        return $value;
    }

}
