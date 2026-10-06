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
        return $this->request('lifecycle', 'GET', '/internal/evidence-bindings/'.$tenant.'/'.$job);
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
        abort_unless(($result['allowed'] ?? null) === true && ($result['audience'] ?? null) === 'assurance'
            && ($result['tenant_id'] ?? null) === $tenant && ($result['action'] ?? null) === $action && ($result['scope'] ?? null) == $scope
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
        $base = config('evidence.'.$owner.'_url');
        $url = is_string($base) ? parse_url($base) : false;
        $ca = config('evidence.'.$owner.'_ca');
        $credential = $this->secrets->read(config('evidence.'.$owner.'_file'));
        abort_unless(is_array($url) && ($url['scheme'] ?? null) === 'https' && isset($url['host'])
            && ! isset($url['user']) && ! isset($url['pass']) && ! isset($url['query']) && ! isset($url['fragment'])
            && ($url['path'] ?? '') === '' && is_string($ca) && str_starts_with($ca, '/') && is_readable($ca) && $credential !== null, 503);
        try {
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeaders($delegation === null ? [] : ['X-Actor-Delegation' => $delegation])
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

            return $result;
        } catch (HttpException $e) {
            throw $e;
        } catch (Throwable) {
            abort(503, 'evidence_owner_unavailable');
        }
    }
}
