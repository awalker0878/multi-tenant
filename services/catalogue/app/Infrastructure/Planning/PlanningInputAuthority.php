<?php

declare(strict_types=1);

namespace App\Infrastructure\Planning;

use App\Application\Planning\Contracts\PlanningInputAuthority as AuthorityContract;
use App\Infrastructure\Foundation\MountedSecret;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Http;
use Symfony\Component\HttpKernel\Exception\HttpException;
use Throwable;

final class PlanningInputAuthority implements AuthorityContract
{
    public function __construct(private readonly MountedSecret $secrets) {}

    /** @param array{site_id: string, environment: string, resource_id: string} $scope
     * @return array<string, mixed> */
    public function check(array $headers, string $tenant, array $scope): array
    {
        $expected = $this->secrets->read(config('planning.credential_file'));
        $outgoing = $this->secrets->read(config('planning.governance_credential_file'));
        $authorization = $headers['authorization'] ?? [];
        $delegations = $headers['x-actor-delegation'] ?? [];
        $actions = $headers['x-planning-action'] ?? [];
        if ($expected === null || $outgoing === null || $expected === $outgoing) {
            throw new HttpException(503, 'source_authority_unavailable');
        }
        if (count($authorization) !== 1 || ! is_string($authorization[0]) || ! hash_equals('Bearer '.$expected, $authorization[0])
            || count($delegations) !== 1 || ! is_string($delegations[0]) || ! preg_match('/\A[0-9a-f]{64}\z/', $delegations[0])
            || count($actions) !== 1 || ! in_array($actions[0], ['plan.read', 'plan.create'], true)) {
            throw new HttpException(403, 'source_access_denied');
        }
        $base = config('planning.governance_url');
        $url = is_string($base) ? parse_url($base) : false;
        $ca = config('planning.ca_file');
        if (! is_array($url) || ($url['scheme'] ?? '') !== 'https' || ! isset($url['host']) || isset($url['user']) || isset($url['pass'])
            || isset($url['query']) || isset($url['fragment']) || ($url['path'] ?? '') !== '' || ! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)) {
            throw new HttpException(503, 'source_authority_unavailable');
        }
        try {
            $response = Http::acceptJson()->asJson()->withToken($outgoing)->withHeader('X-Actor-Delegation', $delegations[0])
                ->connectTimeout(2)->timeout(5)->withOptions(['allow_redirects' => false, 'verify' => $ca])
                ->post($base.'/v1/tenants/'.$tenant.'/planning-input-checks', ['action' => $actions[0], 'scope' => $scope]);
            if (in_array($response->status(), [401, 403, 404], true)) {
                throw new HttpException(403, 'source_access_denied');
            }
            $body = $response->json();
            $returnedScope = is_array($body) ? ($body['scope'] ?? null) : null;
            if (is_array($returnedScope)) {
                ksort($returnedScope, SORT_STRING);
            }
            ksort($scope, SORT_STRING);
            if ($response->status() !== 200 || strlen($response->body()) > 16384 || ! is_array($body)
                || ($body['allowed'] ?? null) !== true || ($body['audience'] ?? null) !== 'planning'
                || ($body['source_owner'] ?? null) !== 'catalogue' || ($body['source_use'] ?? null) !== 'planning_read_only'
                || ($body['tenant_id'] ?? null) !== $tenant || ($body['action'] ?? null) !== $actions[0]
                || $returnedScope !== $scope || ($body['authority_use'] ?? null) !== 'request_bound'
                || Carbon::parse($body['expires_at'])->lessThanOrEqualTo(now()) || Carbon::parse($body['expires_at'])->greaterThan(now()->addSeconds(65))
                || abs(Carbon::parse($body['evaluated_at'])->diffInSeconds(now())) > 5) {
                throw new HttpException(503, 'source_authority_unavailable');
            }

            return $body;
        } catch (HttpException $e) {
            throw $e;
        } catch (Throwable) {
            throw new HttpException(503, 'source_authority_unavailable');
        }
    }
}
