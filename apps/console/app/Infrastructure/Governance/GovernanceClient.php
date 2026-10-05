<?php

declare(strict_types=1);

namespace App\Infrastructure\Governance;

use App\Domain\Identity\IdentityFailure;
use App\Infrastructure\Foundation\MountedSecret;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;

final class GovernanceClient
{
    public function __construct(private readonly MountedSecret $secrets) {}

    /** @param array<string, mixed> $body
     * @return array<string, mixed>
     */
    public function send(string $method, string $path, #[\SensitiveParameter] string $token, #[\SensitiveParameter] array $body = [], ?string $commandKey = null): array
    {
        $base = config('identity.governance_url');
        $url = is_string($base) && filter_var($base, FILTER_VALIDATE_URL) ? parse_url($base) : false;
        $credential = $this->secrets->read(config('identity.credential_file'));
        $ca = config('identity.ca_file');
        if (! is_array($url) || ! isset($url['host'], $url['scheme']) || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment'])
            || ! in_array($url['scheme'], ['https', 'http'], true)
            || ($url['scheme'] === 'http' && ! in_array($url['host'], ['127.0.0.1', 'localhost', '[::1]'], true))
            || ! is_string($credential) || ! preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $credential)
            || ($ca !== null && (! is_string($ca) || ! str_starts_with($ca, '/') || ! is_file($ca) || ! is_readable($ca)))) {
            throw new IdentityFailure(503);
        }
        try {
            $response = Http::acceptJson()->asJson()->withToken($credential)
                ->withHeaders(['X-Console-Session' => $token, ...($commandKey === null ? [] : ['Idempotency-Key' => $commandKey])])->connectTimeout(2)->timeout(5)
                ->withOptions(['allow_redirects' => false, 'verify' => $ca ?? true])
                ->send($method, rtrim((string) $base, '/').$path, ['json' => $body]);
        } catch (ConnectionException) {
            // Never retain HTTP request/body/credential data in exception context.
            throw new IdentityFailure(503);
        }
        if (! $response->successful()) {
            // A bad workload identity is an unavailable dependency, not a browser logout.
            $status = $response->json('error') === 'invalid_workload_identity' ? 503 : $response->status();
            throw new IdentityFailure(in_array($status, [401, 403, 404, 409, 422, 429], true) ? $status : 503);
        }
        $data = $response->json();
        if (! is_array($data) || array_is_list($data)) {
            throw new IdentityFailure(503);
        }

        return $data;
    }
}
