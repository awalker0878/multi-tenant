<?php

declare(strict_types=1);

namespace App\Infrastructure\Catalogue;

use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Domain\Catalogue\CatalogueFailure;
use App\Domain\Identity\IdentityFailure;
use App\Infrastructure\Foundation\MountedSecret;
use App\Infrastructure\Governance\GovernanceClient;
use Illuminate\Support\Facades\Http;
use Opis\JsonSchema\Validator;
use Throwable;

final class CatalogueClient implements CatalogueGateway
{
    public function __construct(private readonly GovernanceClient $governance, private readonly MountedSecret $secrets) {}

    public function permitted(string $session, string $tenant, string $action, ?string $application = null, ?string $environment = null): bool
    {
        try {
            $v = $this->governance->send('POST', '/v1/tenants/'.$tenant.'/authorization-decisions', $session, ['action' => $action, 'scope' => ['site_id' => null, 'environment' => $environment, 'resource_id' => $application]]);

            return ($v['allowed'] ?? false) === true;
        } catch (IdentityFailure $e) {
            if (in_array($e->status, [403, 404], true)) {
                return false;
            } throw $e;
        }
    }

    public function call(string $session, string $tenant, string $operation, array $parameters = [], array $body = [], ?string $key = null, ?string $etag = null, ?string $environment = null, ?string $cursor = null): array
    {
        $spec = GeneratedCatalogueOperations::OPERATIONS[$operation] ?? null;
        if ($spec === null) {
            throw new CatalogueFailure(503);
        }
        $parameters = ['tenant' => $tenant, ...$parameters];
        $path = $spec['path'];
        foreach ($parameters as $field => $value) {
            if (! preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/', $value)) {
                throw new CatalogueFailure(422, 'invalid_identity');
            }$path = str_replace('{'.$field.'}', $value, $path);
        }
        if (str_contains($path, '{')) {
            throw new CatalogueFailure(422, 'missing_identity');
        }
        $base = config('catalogue.url');
        $url = is_string($base) ? parse_url($base) : false;
        $credential = $this->secrets->read(config('catalogue.credential_file'));
        $ca = config('catalogue.ca_file');
        if (! is_array($url) || ($url['scheme'] ?? '') !== 'https' || ! isset($url['host']) || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment']) || ($url['path'] ?? '') !== ''
          || $credential === null || ! preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $credential) || ($ca !== null && (! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)))) {
            throw new CatalogueFailure(503);
        }
        if ($spec['method'] !== 'GET' && str_starts_with($spec['action'], 'application.')) {
            $environment = $body['intent']['environment']['id'] ?? null;
        }
        if (str_starts_with($spec['action'], 'reference.')) {
            $environment = null;
        }
        $delegation = $this->governance->send('POST', '/v1/tenants/'.$tenant.'/actor-delegations', $session, ['audience' => 'catalogue', 'action' => $spec['action'], 'scope' => ['site_id' => null, 'environment' => $environment, 'resource_id' => $parameters['application'] ?? null]]);
        $token = $delegation['delegation_token'] ?? null;
        if (! is_string($token) || ! preg_match('/\A[0-9a-f]{64}\z/', $token) || ($delegation['audience'] ?? null) !== 'catalogue' || ($delegation['authority_use'] ?? null) !== 'request_bound') {
            throw new CatalogueFailure(503);
        }
        $query = array_filter(['environment' => $environment, 'cursor' => $cursor], fn ($v) => $v !== null);
        try {
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeaders(['X-Actor-Delegation' => $token, ...($key === null ? [] : ['Idempotency-Key' => $key]), ...($etag === null ? [] : ['If-Match' => $etag])])
                ->connectTimeout(2)->timeout(10)->withOptions(['allow_redirects' => false, 'verify' => $ca ?? true])
                ->send($spec['method'], $base.$path.($spec['method'] === 'GET' && $query !== [] ? '?'.http_build_query($query) : ''), $spec['method'] === 'GET' ? [] : ['json' => $body === [] ? (object) [] : $body]);
            if (strlen($response->body()) > 310000) {
                throw new CatalogueFailure(503);
            }
            if ($response->status() !== $spec['status']) {
                $reason = $response->json('error');
                $field = $response->json('field');
                throw new CatalogueFailure(in_array($response->status(), [403, 404, 409, 412, 413, 422, 428, 429], true) ? $response->status() : 503,
                    is_string($reason) && preg_match('/\A[a-z_]{1,80}\z/', $reason) ? $reason : 'catalogue_unavailable', is_string($field) && preg_match('/\A[a-zA-Z0-9_.]{1,200}\z/', $field) ? $field : 'intent');
            }
            $wire = $response->json();
            $source = file_get_contents(resource_path('contracts/catalogue-v1.json'));
            if ($source === false) {
                throw new CatalogueFailure(503);
            }
            $api = json_decode($source, true, 512, JSON_THROW_ON_ERROR);
            $schema = ['$ref' => '#/components/schemas/'.$spec['schema'], 'components' => $api['components']];
            if (! is_array($wire) || ! (new Validator)->validate(json_decode($response->body()), json_decode(json_encode($schema, JSON_THROW_ON_ERROR)))->isValid()) {
                throw new CatalogueFailure(503);
            }

            return $wire;
        } catch (CatalogueFailure $e) {
            throw $e;
        } catch (Throwable) {
            throw new CatalogueFailure(503);
        }
    }
}
