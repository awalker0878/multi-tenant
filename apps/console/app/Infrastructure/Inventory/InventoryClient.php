<?php

declare(strict_types=1);

namespace App\Infrastructure\Inventory;

use App\Application\Inventory\Contracts\InventoryGateway;
use App\Domain\Identity\IdentityFailure;
use App\Domain\Inventory\InventoryFailure;
use App\Infrastructure\Foundation\MountedSecret;
use App\Infrastructure\Governance\GovernanceClient;
use Illuminate\Support\Facades\Http;
use Opis\JsonSchema\Validator;
use Throwable;

final class InventoryClient implements InventoryGateway
{
    public function __construct(private readonly GovernanceClient $governance, private readonly MountedSecret $secrets) {}

    public function permitted(string $session, string $tenant, string $action, ?string $site): bool
    {
        try {
            $v = $this->governance->send('POST', '/v1/tenants/'.$tenant.'/authorization-decisions', $session, ['action' => $action, 'scope' => ['site_id' => $site, 'environment' => null, 'resource_id' => null]]);

            return ($v['allowed'] ?? false) === true;
        } catch (IdentityFailure $e) {
            if (in_array($e->status, [403, 404], true)) {
                return false;
            }
            throw $e;
        }
    }

    public function call(string $session, string $tenant, string $operation, array $parameters = [], array $body = [], ?string $key = null, ?int $revision = null, ?string $cursor = null): array
    {
        $spec = GeneratedInventoryOperations::OPERATIONS[$operation] ?? null;
        if ($spec === null) {
            throw new InventoryFailure;
        }
        $path = $spec['path'];
        foreach (['tenant' => $tenant, ...$parameters] as $field => $value) {
            if (! preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/', $value)) {
                throw new InventoryFailure(422, 'invalid_identity');
            }
            $path = str_replace('{'.$field.'}', $value, $path);
        }
        if (str_contains($path, '{')) {
            throw new InventoryFailure(422, 'missing_identity');
        }
        $base = config('inventory.url');
        $url = is_string($base) ? parse_url($base) : false;
        $credential = $this->secrets->read(config('inventory.credential_file'));
        $ca = config('inventory.ca_file');
        if (! is_array($url) || ($url['scheme'] ?? '') !== 'https' || ! isset($url['host']) || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment']) || ($url['path'] ?? '') !== ''
            || $credential === null || ! preg_match('/\A[A-Za-z0-9_-]{32,4096}\z/', $credential) || ! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)) {
            throw new InventoryFailure;
        }
        try {
            $delegation = $this->governance->send('POST', '/v1/tenants/'.$tenant.'/actor-delegations', $session, ['audience' => 'inventory', 'action' => $spec['action'], 'scope' => ['site_id' => $parameters['site'] ?? null, 'environment' => null, 'resource_id' => null]]);
            $token = $delegation['delegation_token'] ?? null;
            if (! is_string($token) || ! preg_match('/\A[0-9a-f]{64}\z/', $token) || ($delegation['audience'] ?? null) !== 'inventory' || ($delegation['authority_use'] ?? null) !== 'request_bound') {
                throw new InventoryFailure;
            }
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeaders(['X-Actor-Delegation' => $token, ...($key === null ? [] : ['Idempotency-Key' => $key]), ...($revision === null ? [] : ['If-Match' => '"'.$revision.'"'])])
                ->connectTimeout(2)->timeout(10)->withOptions(['allow_redirects' => false, 'verify' => $ca, 'stream' => true])
                ->send($spec['method'], $base.$path.($cursor === null ? '' : '?cursor='.rawurlencode($cursor)), $spec['method'] === 'GET' ? [] : ['json' => $body === [] ? (object) [] : $body]);
            $stream = $response->toPsrResponse()->getBody();
            $raw = '';
            try {
                while (! $stream->eof() && strlen($raw) <= 2097152) {
                    $raw .= $stream->read(min(65536, 2097153 - strlen($raw)));
                }
            } finally {
                $stream->close();
            }
            if (strlen($raw) > 2097152) {
                throw new InventoryFailure;
            }
            $wire = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
            if ($response->status() !== $spec['status']) {
                $reason = is_array($wire) ? ($wire['error'] ?? '') : '';
                throw new InventoryFailure(in_array($response->status(), [403, 404, 409, 412, 413, 422, 428, 429], true) ? $response->status() : 503,
                    is_string($reason) && preg_match('/\A[a-z_]{1,80}\z/', $reason) ? $reason : 'inventory_unavailable');
            }
            $source = file_get_contents(resource_path('contracts/inventory-v1.2.json'));
            if ($source === false) {
                throw new InventoryFailure;
            }
            $api = json_decode($source, true, 64, JSON_THROW_ON_ERROR);
            $schema = ['$ref' => '#/components/schemas/'.$spec['schema'], 'components' => $api['components']];
            if (! is_array($wire) || ! (new Validator)->validate(json_decode($raw), json_decode(json_encode($schema, JSON_THROW_ON_ERROR)))->isValid()) {
                throw new InventoryFailure;
            }

            return $wire;
        } catch (InventoryFailure $e) {
            throw $e;
        } catch (IdentityFailure $e) {
            throw new InventoryFailure(in_array($e->status, [401, 403, 404], true) ? 403 : 503);
        } catch (Throwable) {
            throw new InventoryFailure;
        }
    }
}
