<?php

declare(strict_types=1);

namespace App\Infrastructure\Authorization;

use App\Application\Authorization\Contracts\OwnerDirectory;
use App\Application\Authorization\Data\ActorContext;
use App\Domain\Authorization\AccessDenied;
use App\Domain\IntentRevisions\IntentFailure;
use App\Infrastructure\Foundation\MountedSecret;
use Illuminate\Support\Facades\Http;
use Throwable;

final class GovernanceOwnerDirectory implements OwnerDirectory
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function assertOwners(ActorContext $actor, array $owners): void
    {
        $base = config('authorization.governance_url');
        $url = is_string($base) ? parse_url($base) : false;
        $credential = $this->secrets->read(config('authorization.governance_credential_file'));
        $ca = config('authorization.ca_file');
        if (! is_array($url) || ($url['scheme'] ?? '') !== 'https' || ! isset($url['host']) || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment']) || ($url['path'] ?? '') !== ''
            || $credential === null || ! preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $credential)
            || ($ca !== null && (! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)))) {
            throw new AccessDenied(503);
        }
        sort($owners, SORT_STRING);
        try {
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeader('X-Actor-Delegation', $actor->delegationToken)
                ->connectTimeout(2)->timeout(5)->withOptions(['allow_redirects' => false, 'verify' => $ca ?? true])
                ->post($base.'/v1/tenants/'.$actor->tenantId.'/catalogue-owner-checks', ['action' => $actor->action, 'scope' => $actor->scope, 'owners' => $owners]);
            if ($response->status() === 422) {
                throw new IntentFailure('owner_unavailable', 422, 'owners');
            }
            if ($response->status() !== 200) {
                throw new AccessDenied(in_array($response->status(), [401, 403, 404], true) ? 403 : 503);
            }
            $body = $response->json();
            if (! is_array($body) || count($body) !== 3 || ($body['owners'] ?? null) !== $owners || ($body['tenant_id'] ?? null) !== $actor->tenantId || ($body['allowed'] ?? null) !== true) {
                throw new AccessDenied(503);
            }
        } catch (AccessDenied|IntentFailure $e) {
            throw $e;
        } catch (Throwable) {
            throw new AccessDenied(503);
        }
    }
}
