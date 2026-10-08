<?php

declare(strict_types=1);

namespace App\Infrastructure\Approvals;

use App\Application\Approvals\Contracts\ImmutablePlanSource;
use App\Domain\Identity\IdentityDenied;
use App\Infrastructure\Foundation\MountedSecret;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;

final class PlanningPlanSource implements ImmutablePlanSource
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function fetch(string $planId, int $revision): array
    {
        $base = config('governance.planning_url');
        $parts = is_string($base) && filter_var($base, FILTER_VALIDATE_URL) ? parse_url($base) : false;
        $credential = $this->secrets->read(config('governance.planning_credential_file'));
        $ca = config('governance.planning_ca_file');
        if (! is_array($parts) || ($parts['scheme'] ?? null) !== 'https' || ! isset($parts['host'])
            || isset($parts['user']) || isset($parts['pass']) || isset($parts['query']) || isset($parts['fragment'])
            || ! is_string($credential) || ! preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $credential)
            || ($ca !== null && (! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)))) {
            throw new IdentityDenied('plan_authority_unavailable', 503);
        }
        try {
            $response = Http::acceptJson()->withToken($credential)->connectTimeout(2)->timeout(5)
                ->withOptions(['allow_redirects' => false, 'verify' => $ca ?? true])
                ->get(rtrim($base, '/').'/v1/plans/'.$planId.'/revisions/'.$revision);
        } catch (ConnectionException) {
            throw new IdentityDenied('plan_authority_unavailable', 503);
        }
        $body = $response->json();
        if (! $response->successful() || ! is_array($body) || array_is_list($body) || strlen($response->body()) > 65536) {
            throw new IdentityDenied('plan_authority_unavailable', 503);
        }

        return $body;
    }
}
