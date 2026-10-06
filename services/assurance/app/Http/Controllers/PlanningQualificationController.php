<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Planning\Contracts\PlanningInputAuthority;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Throwable;

final class PlanningQualificationController
{
    public function __invoke(Request $request, string $tenant, PlanningInputAuthority $authority): JsonResponse
    {
        abort_if(strlen($request->getContent()) > 32768 || array_diff(array_keys($request->all()), ['scope', 'action', 'qualification_scope']) !== [], 422);
        $input = $request->validate(['scope' => ['required', 'array:site_id,environment,resource_id'],
            'scope.site_id' => ['required', 'uuid', 'lowercase'], 'scope.environment' => ['required', 'uuid', 'lowercase'],
            'scope.resource_id' => ['required', 'uuid', 'lowercase'], 'action' => ['required', 'in:plan.read,plan.create'],
            'qualification_scope' => ['required', 'array:tenant_id,site_id,endpoint_id,native_scope,installed_tuple,action,method,profile_digest,artifacts']]);
        $authority->check($request->headers->all(), $tenant, $input['scope']);
        abort_unless(($input['qualification_scope']['tenant_id'] ?? null) === $tenant && ($input['qualification_scope']['site_id'] ?? null) === $input['scope']['site_id'], 403);
        $path = config('planning.qualification_registry_file');
        // An absent registry is an explicit absence of qualification, never an allow-all default.
        $matches = [];
        if ($path !== null) {
            abort_unless(is_string($path) && str_starts_with($path, '/') && is_readable($path) && filesize($path) <= 524288, 503);
            try {
                $registry = json_decode(file_get_contents($path) ?: '', true, 64, JSON_THROW_ON_ERROR);
                abort_unless(is_array($registry) && ($registry['schema_version'] ?? null) === 1 && is_array($registry['records'] ?? null), 503);
                foreach ($registry['records'] as $record) {
                    if (is_array($record) && $this->canonical($record['scope'] ?? null) === $this->canonical($input['qualification_scope'])) {
                        // Exact record comes from Assurance custody, never a caller-supplied assertion.
                        $matches[] = $record;
                    }
                }
            } catch (Throwable) {
                abort(503);
            }
        }
        abort_if(count($matches) > 1, 503, 'qualification_conflict');
        $result = $matches[0] ?? ['id' => null, 'version' => 1, 'status' => 'unknown', 'scope' => $input['qualification_scope'],
            'evidence_level' => null, 'expires_at' => 0, 'revoked' => false, 'evidence_refs' => [], 'dimensions' => [], 'capabilities' => (object) []];

        return response()->json($result)->header('Cache-Control', 'no-store, private');
    }

    private function canonical(mixed $value): string
    {
        $normalize = function (mixed $v) use (&$normalize): mixed {
            if (! is_array($v)) {
                return $v;
            }
            if (! array_is_list($v)) {
                ksort($v, SORT_STRING);
            }

            return array_map($normalize, $v);
        };

        return json_encode($normalize($value), JSON_THROW_ON_ERROR);
    }
}
