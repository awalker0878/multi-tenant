<?php

declare(strict_types=1);

namespace App\Infrastructure\Jobs;

use App\Application\Jobs\Contracts\JobsGateway;
use App\Domain\Identity\IdentityFailure;
use App\Domain\Jobs\JobsFailure;
use App\Infrastructure\Foundation\MountedSecret;
use App\Infrastructure\Governance\GovernanceClient;
use Illuminate\Support\Facades\Http;
use Opis\JsonSchema\Validator;
use Throwable;

final class JobsClient implements JobsGateway
{
    public function __construct(private readonly GovernanceClient $governance, private readonly MountedSecret $secrets) {}

    public function call(string $session, string $tenant, array $scope, string $method, string $tail, array $body = [], ?string $key = null): array
    {
        $evidence = str_starts_with($tail, 'evidence/');
        if ($evidence && $method !== 'GET') {
            throw new JobsFailure(422, 'invalid_command');
        }
        if (! in_array($method, ['GET', 'POST'], true) || ! preg_match('/\A(?:jobs(?:\/[0-9a-f-]{36})?(?:\/commands)?|evidence\/[0-9a-f-]{36})\z/', $tail)) {
            throw new JobsFailure(422, 'invalid_command');
        }
        foreach ([$tenant, ...array_values($scope)] as $id) {
            if (! preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/', $id)) {
                throw new JobsFailure(422, 'invalid_scope');
            }
        }
        $base = config($evidence ? 'jobs.evidence_url' : 'jobs.url');
        $url = is_string($base) ? parse_url($base) : false;
        $ca = config($evidence ? 'jobs.evidence_ca' : 'jobs.ca_file');
        $credential = $this->secrets->read(config($evidence ? 'jobs.evidence_file' : 'jobs.credential_file'));
        if (! is_array($url) || ($url['scheme'] ?? '') !== 'https' || ! isset($url['host']) || isset($url['user']) || isset($url['pass'])
            || isset($url['query']) || isset($url['fragment']) || ($url['path'] ?? '') !== '' || $credential === null
            || ! is_string($ca) || ! str_starts_with($ca, '/') || ! is_readable($ca)) {
            throw new JobsFailure;
        }
        try {
            $action = $evidence ? 'evidence.read' : ($method === 'GET' ? 'operation.read' : ($tail === 'jobs' ? 'operation.admit' : 'operation.control'));
            $delegation = $this->governance->send('POST', '/v1/tenants/'.$tenant.'/actor-delegations', $session, ['audience' => $evidence ? 'assurance' : 'lifecycle', 'action' => $action, 'scope' => $scope]);
            if (! is_string($delegation['delegation_token'] ?? null) || ! preg_match('/\A[0-9a-f]{64}\z/', $delegation['delegation_token'])
                || ($delegation['audience'] ?? null) !== ($evidence ? 'assurance' : 'lifecycle') || ($delegation['authority_use'] ?? null) !== 'request_bound') {
                throw new JobsFailure;
            }
            $response = Http::acceptJson()->asJson()->withToken($credential)->withHeaders(['X-Actor-Delegation' => $delegation['delegation_token'], ...($key === null ? [] : ['Idempotency-Key' => $key])])
                ->connectTimeout(2)->timeout(45)->withOptions(['allow_redirects' => false, 'verify' => $ca, 'stream' => true])
                ->send($method, $base.'/v1/tenants/'.$tenant.'/'.$tail, $method === 'GET' ? [] : ['json' => $body]);
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
                throw new JobsFailure;
            }
            $result = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
            if (! in_array($response->status(), [200, 202], true)) {
                $reason = is_array($result) ? ($result['error'] ?? '') : '';
                throw new JobsFailure(in_array($response->status(), [401, 403, 404, 409, 422, 423, 429], true) ? $response->status() : 503,
                    is_string($reason) && preg_match('/\A[a-z_]{1,80}\z/', $reason) ? $reason : 'jobs_unavailable');
            }
            if (! is_array($result) || array_is_list($result)) {
                throw new JobsFailure;
            }
            $contract = json_decode(file_get_contents(resource_path('contracts/lifecycle-v1.json')) ?: '', true, 64, JSON_THROW_ON_ERROR);
            $schema = ['$ref' => '#/components/schemas/'.($evidence ? 'EvidenceRecord' : (str_ends_with($tail, '/commands') ? 'CommandReceipt' : 'Job')), 'components' => $contract['components']];
            if (! (new Validator)->validate(json_decode($raw), json_decode(json_encode($schema, JSON_THROW_ON_ERROR)))->isValid()) {
                throw new JobsFailure;
            }
            if (! str_ends_with($tail, '/commands') && (($result['tenant_id'] ?? null) !== $tenant || array_intersect_key($result['scope'], $scope) != $scope)) {
                throw new JobsFailure(403, 'scope_mismatch');
            }

            if (! $evidence && $method === 'GET') {
                $result['control_allowed'] = false;
                try {
                    $control = $this->governance->send('POST', '/v1/tenants/'.$tenant.'/actor-delegations', $session,
                        ['audience' => 'lifecycle', 'action' => 'operation.control', 'scope' => $scope]);
                    $result['control_allowed'] = ($control['audience'] ?? null) === 'lifecycle' && ($control['authority_use'] ?? null) === 'request_bound';
                } catch (IdentityFailure) {
                    // A read grant never implies control authority. Every actual command is reauthorized.
                }
            }

            return $result;
        } catch (JobsFailure $e) {
            throw $e;
        } catch (IdentityFailure $e) {
            throw new JobsFailure(in_array($e->status, [401, 403, 404], true) ? 403 : 503);
        } catch (Throwable) {
            throw new JobsFailure;
        }
    }
}
