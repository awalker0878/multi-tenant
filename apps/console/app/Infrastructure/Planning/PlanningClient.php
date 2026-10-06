<?php

declare(strict_types=1);

namespace App\Infrastructure\Planning;

use App\Application\Planning\Contracts\PlanningGateway;
use App\Domain\Identity\IdentityFailure;
use App\Domain\Planning\PlanningFailure;
use App\Infrastructure\Foundation\MountedSecret;
use App\Infrastructure\Governance\GovernanceClient;
use Illuminate\Support\Facades\Http;
use Opis\JsonSchema\Validator;
use Throwable;

final class PlanningClient implements PlanningGateway
{
    public function __construct(private readonly GovernanceClient $governance, private readonly MountedSecret $secrets) {}

    public function call(string $session, string $tenant, string $application, string $environment, string $method, string $tail, array $sites, array $body = [], ?string $key = null): array
    {
        if (count($sites) < 1 || count($sites) > 3 || ! in_array($method, ['GET', 'POST'], true)
            || ! preg_match('/\A(?:assessments|plans)(?:\/[0-9a-f-]{36})?(?:\/(?:validity|diff))?\z/', $tail)) {
            throw new PlanningFailure(422, 'invalid_scope');
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
            $tokens = [];
            $action = $method === 'POST' && ! str_ends_with($tail, '/validity') && ! str_ends_with($tail, '/diff') ? 'plan.create' : 'plan.read';
            foreach (array_unique($sites) as $site) {
                $d = $this->governance->send('POST', '/v1/tenants/'.$tenant.'/actor-delegations', $session, ['audience' => 'planning', 'action' => $action,
                    'scope' => ['site_id' => $site, 'environment' => $environment, 'resource_id' => $application]]);
                if (! is_string($d['delegation_token'] ?? null) || ! preg_match('/\A[0-9a-f]{64}\z/', $d['delegation_token'])
                    || ($d['audience'] ?? null) !== 'planning' || ($d['authority_use'] ?? null) !== 'request_bound') {
                    throw new PlanningFailure;
                }
                $tokens[] = $site.':'.$d['delegation_token'];
            }
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeaders(['X-Planning-Delegations' => implode(',', $tokens), ...($key === null ? [] : ['Idempotency-Key' => $key])])
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
            if (! in_array($response->status(), [200, 201], true)) {
                $reason = is_array($result) ? ($result['error'] ?? '') : '';
                throw new PlanningFailure(in_array($response->status(), [401, 403, 404, 409, 422, 429], true) ? $response->status() : 503,
                    is_string($reason) && preg_match('/\A[a-z_]{1,80}\z/', $reason) ? $reason : 'planning_unavailable');
            }
            if (! is_array($result) || array_is_list($result)) {
                throw new PlanningFailure;
            }

            $api = json_decode(file_get_contents(resource_path('contracts/planning-v1.json')) ?: '', true, 64, JSON_THROW_ON_ERROR);
            $schemaName = $response->status() === 201 ? 'Receipt' : (str_ends_with($tail, '/validity') ? 'Validity' : (str_ends_with($tail, '/diff') ? 'Diff' : (str_starts_with($tail, 'plans/') ? 'Plan' : 'Assessment')));
            $schema = ['$ref' => '#/components/schemas/'.$schemaName, 'components' => $api['components']];
            if (! (new Validator)->validate(json_decode($raw), json_decode(json_encode($schema, JSON_THROW_ON_ERROR)))->isValid()) {
                throw new PlanningFailure;
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
