<?php

declare(strict_types=1);

namespace App\Infrastructure\Identity;

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Application\Identity\Data\ConsoleSession;
use App\Domain\Identity\IdentityFailure;
use App\Infrastructure\Governance\GovernanceClient;

final class GovernanceIdentityGateway implements IdentityGateway
{
    public function __construct(private readonly GovernanceClient $http) {}

    public function login(string $username, #[\SensitiveParameter] string $password): ConsoleSession
    {
        return $this->session($this->http->send('POST', '/identity/local-sessions', '', ['username' => $username, 'password' => $password]));
    }

    public function current(#[\SensitiveParameter] string $token): ConsoleActor
    {
        return $this->actor($this->http->send('GET', '/identity/session', $token));
    }

    public function changePassword(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $currentPassword, #[\SensitiveParameter] string $password): ConsoleSession
    {
        return $this->session($this->http->send('POST', '/identity/password', $token, ['current_password' => $currentPassword, 'password' => $password, 'password_confirmation' => $password]));
    }

    public function logout(#[\SensitiveParameter] string $token): void
    {
        $this->http->send('POST', '/identity/logout', $token);
    }

    /** @return array<string, mixed> */
    public function settings(#[\SensitiveParameter] string $token): array
    {
        return $this->http->send('GET', '/identity/oidc', $token);
    }

    public function saveSettings(#[\SensitiveParameter] string $token, #[\SensitiveParameter] array $settings): void
    {
        $this->http->send('PUT', '/identity/oidc', $token, $settings);
    }

    public function begin(string $purpose, #[\SensitiveParameter] string $binding, #[\SensitiveParameter] string $token): string
    {
        $data = $this->http->send('POST', '/identity/oidc/flows', $token, ['purpose' => $purpose, 'browser_binding' => $binding]);
        $url = $data['authorization_url'] ?? null;
        if (! is_string($url) || ! filter_var($url, FILTER_VALIDATE_URL) || parse_url($url, PHP_URL_SCHEME) !== 'https'
            || parse_url($url, PHP_URL_USER) !== null || parse_url($url, PHP_URL_PASS) !== null) {
            throw new IdentityFailure(503);
        }

        return $url;
    }

    public function callback(#[\SensitiveParameter] string $state, #[\SensitiveParameter] string $binding, #[\SensitiveParameter] string $code, #[\SensitiveParameter] string $token): ConsoleSession|array
    {
        $data = $this->http->send('POST', '/identity/oidc/callback', $token, ['state' => $state, 'browser_binding' => $binding, 'code' => $code]);
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
        return $this->session($this->http->send('POST', '/identity/oidc/activation', $token, ['verification_token' => $proof]));
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
