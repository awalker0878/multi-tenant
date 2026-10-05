<?php

declare(strict_types=1);

namespace App\Infrastructure\Authorization;

use App\Application\Authorization\Contracts\DelegatedAuthority;
use App\Application\Authorization\Data\ActorContext;
use App\Domain\Authorization\AccessDenied;
use App\Infrastructure\Foundation\MountedSecret;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Http;
use Throwable;

final class GovernanceDelegatedAuthority implements DelegatedAuthority
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function check(#[\SensitiveParameter] string $token, string $tenant, string $action, array $scope): ActorContext
    {
        $base = config('authorization.governance_url');
        $url = is_string($base) && filter_var($base, FILTER_VALIDATE_URL) ? parse_url($base) : false;
        $credential = $this->secrets->read(config('authorization.governance_credential_file'));
        $ca = config('authorization.ca_file');
        if (! is_array($url) || ($url['scheme'] ?? '') !== 'https' || ! isset($url['host']) || isset($url['user']) || isset($url['pass'])
            || isset($url['query']) || isset($url['fragment']) || ($url['path'] ?? '') !== ''
            || $credential === null || ! preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $credential)
            || ($ca !== null && (! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)))) {
            throw new AccessDenied(503);
        }
        if (! preg_match('/\A[0-9a-f]{64}\z/', $token) || ! $this->uuid($tenant)
            || ! in_array($action, ['application.read', 'application.write'], true)) {
            throw new AccessDenied;
        }
        try {
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeader('X-Actor-Delegation', $token)
                ->connectTimeout(2)->timeout(5)->withOptions(['allow_redirects' => false, 'verify' => $ca ?? true])
                ->post($base.'/v1/tenants/'.$tenant.'/delegated-authorizations', ['action' => $action, 'scope' => $scope]);
            if ($response->status() !== 200) {
                throw new AccessDenied(in_array($response->status(), [401, 403, 404], true) ? 403 : 503);
            }
            $body = $response->json();
            if (! is_array($body) || ($body['allowed'] ?? false) !== true || ($body['audience'] ?? '') !== 'catalogue'
                || ($body['delegating_service'] ?? '') !== 'console' || ($body['authority_use'] ?? '') !== 'request_bound'
                || ($body['tenant_id'] ?? '') !== $tenant || ($body['action'] ?? '') !== $action || ! $this->sameScope($body['scope'] ?? null, $scope)
                || ! $this->uuid($body['actor_id'] ?? null) || ! $this->uuid($body['delegation_id'] ?? null)
                || ! is_string($body['expires_at'] ?? null) || ! is_string($body['evaluated_at'] ?? null)
                || Carbon::parse($body['expires_at'])->lessThanOrEqualTo(now())
                || Carbon::parse($body['expires_at'])->greaterThan(now()->addSeconds(65))
                || abs(Carbon::parse($body['evaluated_at'])->diffInSeconds(now())) > 5) {
                throw new AccessDenied(503);
            }

            return new ActorContext($body['actor_id'], $tenant, $action, $scope, $body['delegation_id']);
        } catch (AccessDenied $error) {
            throw $error;
        } catch (Throwable) {
            // Requests, credentials and upstream exceptions never enter logs.
            throw new AccessDenied(503);
        }
    }

    private function uuid(mixed $value): bool
    {
        return is_string($value) && preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/', $value) === 1;
    }

    /** @param array{site_id: ?string, environment: ?string, resource_id: ?string} $expected */
    private function sameScope(mixed $given, array $expected): bool
    {
        if (! is_array($given)) {
            return false;
        }
        ksort($given);
        ksort($expected);

        return $given === $expected;
    }
}
