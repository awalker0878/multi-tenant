<?php

declare(strict_types=1);

namespace App\Infrastructure\Planning;

use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Identity\IdentityFailure;
use App\Domain\Planning\PlanningFailure;
use App\Infrastructure\Foundation\MountedSecret;
use App\Infrastructure\Governance\GovernanceClient;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Opis\JsonSchema\Validator;
use Throwable;

final class PlanningClient implements PlanningGateway
{
    public function __construct(private readonly GovernanceClient $governance, private readonly MountedSecret $secrets) {}

    public function call(string $session, string $tenant, string $application, string $environment, string $method, string $tail, array $sites, array $body = [], ?string $key = null): array
    {
        $migration = in_array($tail, ['migration-preparations', 'migration-plans', 'migration-plan-options', 'migration-support', 'migration-flow-choices', 'migration-flow-selections', 'migration-workload-readiness'], true);
        if (($migration && ($method !== 'POST' || count($sites) !== 1)) || count($sites) < 1 || count($sites) > 3 || ! in_array($method, ['GET', 'POST'], true)
            || (! $migration && ! preg_match('/\A(?:assessments|plans)(?:\/[0-9a-f-]{36})?(?:\/(?:validity|diff))?\z/', $tail))) {
            throw new PlanningFailure(422, 'invalid_scope');
        }
        if ($migration && $key === null) {
            if (! in_array($tail, ['migration-preparations', 'migration-plan-options', 'migration-support', 'migration-flow-choices', 'migration-workload-readiness'], true)) {
                throw new PlanningFailure(422, 'idempotency_key_required');
            }
            $key = (string) Str::uuid();
        }
        foreach ([$tenant, $application, $environment, ...$sites] as $id) {
            if (! preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/', $id)) {
                throw new PlanningFailure(422, 'invalid_scope');
            }
        }
        $base = config('planning.url');
        $url = is_string($base) ? parse_url($base) : false;
        $credential = $this->secrets->read(config('planning.credential_file'));
        $ca = config('planning.ca_file');
        if (! is_array($url) || ($url['scheme'] ?? '') !== 'https' || ! isset($url['host']) || isset($url['user']) || isset($url['pass'])
            || isset($url['query']) || isset($url['fragment']) || ($url['path'] ?? '') !== '' || $credential === null
            || ! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)) {
            throw new PlanningFailure;
        }
        try {
            $api = json_decode(file_get_contents(resource_path($migration ? 'contracts/planning-migration-v2.json' : 'contracts/planning-v1.2.json')) ?: '', true, 64, JSON_THROW_ON_ERROR);
            $template = preg_replace('/\/[0-9a-f-]{36}(?=\/|\z)/', '/{record}', $tail);
            $operation = $api['paths']['/v1/tenants/{tenant}/applications/{application}/environments/{environment}/'.$template][strtolower($method)] ?? null;
            if (! is_array($operation)) {
                throw new PlanningFailure(422, 'invalid_scope');
            }
            $tokens = [];
            $action = $method === 'POST' && ! in_array($tail, ['migration-support', 'migration-flow-choices', 'migration-workload-readiness'], true) && ! str_ends_with($tail, '/validity') && ! str_ends_with($tail, '/diff') ? 'plan.create' : 'plan.read';
            foreach (array_unique($sites) as $site) {
                $d = $this->governance->send('POST', '/v1/tenants/'.$tenant.'/actor-delegations', $session, ['audience' => 'planning', 'action' => $action,
                    'scope' => ['site_id' => $site, 'environment' => $environment, 'resource_id' => $application]]);
                if (! is_string($d['delegation_token'] ?? null) || ! preg_match('/\A[0-9a-f]{64}\z/', $d['delegation_token'])
                    || ($d['audience'] ?? null) !== 'planning' || ($d['authority_use'] ?? null) !== 'request_bound') {
                    throw new PlanningFailure;
                }
                $tokens[] = $site.':'.$d['delegation_token'];
            }
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeaders([...($migration ? ['X-Actor-Delegation' => explode(':', $tokens[0], 2)[1]] : ['X-Planning-Delegations' => implode(',', $tokens)]), ...($key === null ? [] : ['Idempotency-Key' => $key])])
                ->connectTimeout(2)->timeout(45)->withOptions(['allow_redirects' => false, 'verify' => $ca, 'stream' => true])
                ->send($method, $base.'/v1/tenants/'.$tenant.'/applications/'.$application.'/environments/'.$environment.'/'.$tail, $method === 'GET' ? [] : ['json' => $body === [] ? (object) [] : $body]);
            $stream = $response->toPsrResponse()->getBody();
            $raw = '';
            try {
                while (! $stream->eof() && strlen($raw) <= 1048576) {
                    $raw .= $stream->read(min(65536, 1048577 - strlen($raw)));
                }
            } finally {
                $stream->close();
            }
            if (strlen($raw) > 1048576) {
                throw new PlanningFailure;
            }
            $result = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
            if ($response->status() < 200 || $response->status() >= 300) {
                if ($migration) {
                    $errorSchema = ['$ref' => '#/components/schemas/Error', 'components' => $api['components']];
                    if (! (new Validator)->validate(json_decode($raw), json_decode(json_encode($errorSchema, JSON_THROW_ON_ERROR)))->isValid()) {
                        throw new PlanningFailure;
                    }
                }
                $reason = is_array($result) ? ($result[$migration ? 'code' : 'error'] ?? '') : '';
                throw new PlanningFailure(in_array($response->status(), [401, 403, 404, 409, 412, 422, 423, 429], true) ? $response->status() : 503,
                    is_string($reason) && preg_match($migration ? '/\A[a-z][a-z0-9_.-]{2,95}\z/' : '/\A[a-z_]{1,80}\z/', $reason) ? $reason : 'planning_unavailable');
            }
            if (! is_array($result) || array_is_list($result)) {
                throw new PlanningFailure;
            }

            $responseSchema = $operation['responses'][(string) $response->status()]['content']['application/json']['schema'] ?? null;
            if (! is_array($responseSchema)) {
                throw new PlanningFailure;
            }
            $schema = [...$responseSchema, 'components' => $api['components']];
            if (! (new Validator)->validate(json_decode($raw), json_decode(json_encode($schema, JSON_THROW_ON_ERROR)))->isValid()) {
                throw new PlanningFailure;
            }
            if (! $migration && $method === 'GET') {
                if (($result['id'] ?? null) !== explode('/', $tail)[1]
                    || ($result['tenant_id'] ?? null) !== $tenant
                    || ($result['application_id'] ?? null) !== $application
                    || ($result['environment'] ?? null) !== $environment) {
                    throw new PlanningFailure(403, 'scope_mismatch');
                }
            }
            if (in_array($tail, ['assessments', 'plans', 'migration-plans'], true)
                && ($result['kind'] ?? null) !== ($tail === 'assessments' ? 'assessment' : 'plan')) {
                throw new PlanningFailure(403, 'scope_mismatch');
            }
            if ($tail === 'plans' || $tail === 'migration-plans' || (! $migration && $method === 'GET' && str_starts_with($tail, 'plans/'))) {
                $binding = $result['binding'] ?? [];
                if (($binding['plan_id'] ?? null) !== $result['id'] || ($binding['tenant_id'] ?? null) !== $tenant
                    || ($binding['resource_id'] ?? null) !== $application || ($binding['environment'] ?? null) !== $environment
                    || ! in_array($binding['site_id'] ?? null, $sites, true)) {
                    throw new PlanningFailure(403, 'scope_mismatch');
                }
                if ($method === 'GET' && (array_intersect_key($result['content']['scope'], array_flip(['tenant_id', 'resource_id', 'environment', 'site_id']))
                    != array_intersect_key($binding, array_flip(['tenant_id', 'resource_id', 'environment', 'site_id'])))) {
                    throw new PlanningFailure(403, 'scope_mismatch');
                }
            }

            return $result;
        } catch (PlanningFailure $e) {
            throw $e;
        } catch (IdentityFailure $e) {
            throw new PlanningFailure(in_array($e->status, [401, 403, 404], true) ? 403 : 503);
        } catch (Throwable) {
            throw new PlanningFailure;
        }
    }
}
