<?php

declare(strict_types=1);

namespace App\Infrastructure\Identity;

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Identity\Data\ConsoleSession;
use App\Domain\Identity\IdentityFailure;
use App\Infrastructure\Foundation\MountedSecret;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;

final class GovernanceIdentityGateway implements IdentityGateway
{
    public function __construct(private readonly MountedSecret $secrets) {}

    public function login(string $username, #[\SensitiveParameter] string $password): ConsoleSession
    {
        return $this->session($this->send('POST', '/identity/local-sessions', '', ['username' => $username, 'password' => $password]));
    }

    public function current(#[\SensitiveParameter] string $token): ConsoleActor
    {
        return $this->actor($this->send('GET', '/identity/session', $token));
    }

    public function changePassword(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $currentPassword, #[\SensitiveParameter] string $password): ConsoleSession
    {
        return $this->session($this->send('POST', '/identity/password', $token, ['current_password' => $currentPassword, 'password' => $password, 'password_confirmation' => $password]));
    }

    public function logout(#[\SensitiveParameter] string $token): void
    {
        $this->send('POST', '/identity/logout', $token);
    }

    /** @return array<string, mixed> */
    public function settings(#[\SensitiveParameter] string $token): array
    {
        return $this->send('GET', '/identity/oidc', $token);
    }

    public function saveSettings(#[\SensitiveParameter] string $token, #[\SensitiveParameter] array $settings): void
    {
        $this->send('PUT', '/identity/oidc', $token, $settings);
    }

    public function begin(string $purpose, #[\SensitiveParameter] string $binding, #[\SensitiveParameter] string $token): string
    {
        $data = $this->send('POST', '/identity/oidc/flows', $token, ['purpose' => $purpose, 'browser_binding' => $binding]);
        $url = $data['authorization_url'] ?? null;
        if (! is_string($url) || ! filter_var($url, FILTER_VALIDATE_URL) || parse_url($url, PHP_URL_SCHEME) !== 'https'
            || parse_url($url, PHP_URL_USER) !== null || parse_url($url, PHP_URL_PASS) !== null) {
            throw new IdentityFailure(503);
        }

        return $url;
    }

    public function callback(#[\SensitiveParameter] string $state, #[\SensitiveParameter] string $binding, #[\SensitiveParameter] string $code, #[\SensitiveParameter] string $token): ConsoleSession|array
    {
        $data = $this->send('POST', '/identity/oidc/callback', $token, ['state' => $state, 'browser_binding' => $binding, 'code' => $code]);
        if (isset($data['session_token'])) {
            return $this->session($data);
        }
        if (! is_string($data['verification_token'] ?? null) || ! preg_match('/\A[0-9a-f]{64}\z/', $data['verification_token']) || ! is_int($data['revision'] ?? null)) {
            throw new IdentityFailure(503);
        }

        return ['verification_token' => $data['verification_token'], 'revision' => $data['revision']];
    }

    public function activate(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $proof): ConsoleSession
    {
        return $this->session($this->send('POST', '/identity/oidc/activation', $token, ['verification_token' => $proof]));
    }

    /** @param array<string, mixed> $body
     * @return array<string, mixed>
     */
    private function send(string $method, string $path, #[\SensitiveParameter] string $token, #[\SensitiveParameter] array $body = []): array
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
                ->withHeaders(['X-Console-Session' => $token])->connectTimeout(2)->timeout(5)
                ->withOptions(['allow_redirects' => false, 'verify' => $ca ?? true])
                ->send($method, rtrim((string) $base, '/').$path, ['json' => $body]);
        } catch (ConnectionException) {
            // Never retain HTTP request/body/credential data in exception context.
            throw new IdentityFailure(503);
        }
        if (! $response->successful()) {
            // A bad workload identity is an unavailable dependency, not a browser logout.
            $status = $response->json('error') === 'invalid_workload_identity' ? 503 : $response->status();
            throw new IdentityFailure(in_array($status, [401, 403, 409, 422, 429], true) ? $status : 503);
        }
        $data = $response->json();
        if (! is_array($data) || array_is_list($data)) {
            throw new IdentityFailure(503);
        }

        return $data;
    }

    /** @param array<string, mixed> $data */
    private function actor(array $data): ConsoleActor
    {
        $identity = $data['identity'] ?? null;
        if (! is_array($identity) || ! is_string($identity['subject'] ?? null) || ! is_bool($identity['password_change_required'] ?? null)) {
            throw new IdentityFailure(503);
        }
        $federated = ($identity['kind'] ?? null) === 'federated';
        if (($federated && (! preg_match('/\A[0-9a-f-]{36}\z/', $identity['subject']) || $identity['password_change_required']))
            || (! $federated && $identity['subject'] !== 'bootstrap-admin')) {
            throw new IdentityFailure(503);
        }

        return new ConsoleActor($identity['password_change_required'], $identity['subject'], $federated, $federated && in_array('identity.setup', (array) ($identity['permissions'] ?? []), true));
    }

    /** @param array<string, mixed> $data */
    private function session(#[\SensitiveParameter] array $data): ConsoleSession
    {
        $token = $data['session_token'] ?? null;
        if (! is_string($token) || ! preg_match('/\A[0-9a-f]{64}\z/', $token)) {
            throw new IdentityFailure(503);
        }

        return new ConsoleSession($token, $this->actor($data));
    }
}
