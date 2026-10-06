<?php

declare(strict_types=1);

// Disposable campaign bootstrap only. Real owner actions and runtime privileges;
// the synthetic OIDC transport exists in this separate fixture process alone.
if (getenv('GITHUB_ACTIONS') !== 'true' || getenv('P03_TEST_POSTGRES') !== '1') {
    exit(2);
}
$root = dirname(__DIR__, 2);
require $root.'/services/governance/vendor/autoload.php';
$app = require $root.'/services/governance/bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Http\Kernel::class);
$kernel->bootstrap();
$provider = new Tests\Support\SyntheticOidcTransport;
$app->instance(App\Application\Identity\Contracts\OidcHttpTransport::class, $provider);
$credential = trim(file_get_contents(getenv('CONSOLE_CREDENTIAL_FILE')));
$call = function (string $method, string $path, array $body = [], string $token = '', int $status = 200) use ($kernel, $credential): array {
    $request = Illuminate\Http\Request::create($path, $method, [], [], [], [
        'HTTP_AUTHORIZATION' => 'Bearer '.$credential, 'HTTP_X_CONSOLE_SESSION' => $token,
        'HTTP_IDEMPOTENCY_KEY' => bin2hex(random_bytes(16)), 'HTTP_ACCEPT' => 'application/json', 'CONTENT_TYPE' => 'application/json',
    ], json_encode($body, JSON_THROW_ON_ERROR));
    $response = $kernel->handle($request);
    $value = json_decode($response->getContent(), true, 512, JSON_THROW_ON_ERROR);
    $kernel->terminate($request, $response);
    if ($response->getStatusCode() !== $status) {
        throw new RuntimeException('seed_request_failed:'.$path.':'.$response->getStatusCode());
    }
    return $value;
};
$temporary = app(App\Application\Identity\Actions\BootstrapAdministrator::class)->handle();
$local = $call('POST', '/identity/local-sessions', ['username' => 'admin', 'password' => $temporary])['session_token'];
$replacement = bin2hex(random_bytes(32));
$local = $call('POST', '/identity/password', ['current_password' => $temporary, 'password' => $replacement, 'password_confirmation' => $replacement], $local)['session_token'];
$call('PUT', '/identity/oidc', ['revision' => 0, 'issuer' => 'https://idp.example.test/realm', 'client_id' => 'console-client',
    'client_secret' => 'synthetic-oidc-secret', 'redirect_uri' => 'https://console.example.test/identity/callback',
    'administrator_subject' => 'immutable-admin-subject', 'private_networks' => []], $local, 201);
$login = function (string $purpose, string $token, string $subject) use ($call, $provider): array {
    $binding = bin2hex(random_bytes(32));
    $url = $call('POST', '/identity/oidc/flows', ['purpose' => $purpose, 'browser_binding' => $binding], $token)['authorization_url'];
    $provider->claims = ['sub' => $subject];
    return $call('POST', '/identity/oidc/callback', $provider->authorize($url) + ['browser_binding' => $binding]);
};
$proof = $login('setup', $local, 'immutable-admin-subject')['verification_token'];
$admin = $call('POST', '/identity/oidc/activation', ['verification_token' => $proof], $local)['session_token'];
$tenant = $call('POST', '/v1/tenants', ['name' => 'P03 Permit Desk', 'administrator_subject' => 'immutable-admin-subject'], $admin, 201)['id'];
$foreign = $call('POST', '/v1/tenants', ['name' => 'P03 Separate Tenant', 'administrator_subject' => 'immutable-admin-subject'], $admin, 201)['id'];
$member = $call('POST', '/v1/tenants/'.$tenant.'/memberships', ['revision' => 0, 'subject' => 'p03-author', 'role' => 'author', 'state' => 'active', 'site_id' => null, 'environment' => null, 'expires_at' => null], $admin);
$author = $login('login', '', 'p03-author')['session_token'];
$actor = $call('GET', '/identity/session', [], $author);
$result = ['tenant' => $tenant, 'foreign_tenant' => $foreign, 'admin_token' => $admin, 'author_token' => $author,
    'actor_id' => $member['actor_id'], 'membership' => $member];
file_put_contents($argv[1], json_encode($result, JSON_THROW_ON_ERROR));
chmod($argv[1], 0600);
echo "Synthetic principals created using Governance owner actions.\n";
