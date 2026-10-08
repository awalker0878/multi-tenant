<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Foundation\Contracts\SecretReader;
use App\Application\Qualification\Actions\ResolveQualification;
use App\Domain\Qualification\NativeQualification;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Throwable;

/** Service-only current support read; requests cannot publish qualification. */
final class MigrationQualificationController
{
    public function __invoke(Request $request, string $tenant, SecretReader $secrets): JsonResponse
    {
        $token = $secrets->read(config('planning.credential_file'));
        $outgoing = $secrets->read(config('planning.governance_credential_file'));
        abort_if($token === null || $outgoing === null || $token === $outgoing, 503);
        $authorization = $request->headers->all('authorization');
        abort_unless(count($authorization) === 1 && is_string($authorization[0]) && hash_equals('Bearer '.$token, $authorization[0]), 403);
        abort_if(strlen($request->getContent()) > 32768 || array_diff(array_keys($request->all()), ['scope', 'tranche_sha256', 'release_sha256']) !== [], 422);
        $input = $request->validate([
            'scope' => ['required', 'array:tenant_id,site_id,resource_id,environment'],
            'scope.tenant_id' => ['required', 'uuid', 'lowercase'],
            'scope.site_id' => ['required', 'uuid', 'lowercase'],
            'scope.resource_id' => ['required', 'uuid', 'lowercase'],
            'scope.environment' => ['required', 'uuid', 'lowercase'],
            'tranche_sha256' => ['required', 'regex:/\A[a-f0-9]{64}\z/'],
            'release_sha256' => ['required', 'regex:/\A[a-f0-9]{64}\z/'],
        ]);
        abort_unless($input['scope']['tenant_id'] === $tenant, 403);
        $path = config('planning.migration_support_registry_file');
        $records = [];
        if ($path !== null) {
            abort_unless(is_string($path) && str_starts_with($path, '/') && ! is_link($path) && is_file($path) && is_readable($path), 503);
            for ($parent = dirname($path); $parent !== '/'; $parent = dirname($parent)) {
                abort_if(is_link($parent), 503);
            }
            $handle = fopen($path, 'rb');
            abort_unless($handle !== false, 503);
            try {
                $info = fstat($handle);
                abort_unless(is_array($info) && ($info['mode'] & 0170000) === 0100000 && ($info['mode'] & 0022) === 0 && $info['size'] <= 2097152, 503);
                $raw = stream_get_contents($handle, 2097153);
                abort_unless(is_string($raw) && strlen($raw) <= 2097152, 503);
                $registry = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
                abort_unless(is_array($registry) && ($registry['schema_version'] ?? null) === 1 && is_array($registry['assignments'] ?? null) && count($registry['assignments']) <= 256, 503);
                $expectedScope = $input['scope'];
                ksort($expectedScope, SORT_STRING);
                $matches = [];
                foreach ($registry['assignments'] as $row) {
                    if (! is_array($row) || ! is_array($row['scope'] ?? null)) {
                        continue;
                    }
                    $scope = $row['scope'];
                    ksort($scope, SORT_STRING);
                    if ($scope === $expectedScope && ($row['tranche_sha256'] ?? null) === $input['tranche_sha256'] && ($row['release_sha256'] ?? null) === $input['release_sha256']) {
                        $matches[] = $row;
                    }
                }
                abort_if(count($matches) > 1, 503, 'migration_support_conflict');
                $records = $matches[0]['records'] ?? [];
                abort_unless(is_array($records) && array_is_list($records) && count($records) <= 512, 503);
                $assignment = $matches[0] ?? [];
                $qualificationScope = $assignment['qualification_scope'] ?? null;
                if (! is_array($qualificationScope)) {
                    $records = [];
                } else {
                    $resolved = (new ResolveQualification)->handle($qualificationScope);
                    $binding = NativeQualification::digest([...$input, 'records' => $records]);
                    $capability = $resolved['capabilities']['migration.support_records'] ?? [];
                    if (($resolved['verification']['valid'] ?? false) !== true
                        || ($qualificationScope['tenant_id'] ?? null) !== $tenant
                        || ($qualificationScope['site_id'] ?? null) !== $input['scope']['site_id']
                        || ($capability['status'] ?? null) !== 'supported'
                        || ! in_array($binding, $capability['values'] ?? [], true)) {
                        $records = [];
                    }
                    if (($resolved['evidence_level'] ?? null) !== 'E4') {
                        $records = array_values(array_filter($records, fn (array $record): bool => ($record['level'] ?? null) !== 'E4'));
                    }
                }
            } catch (Throwable) {
                abort(503, 'migration_support_unavailable');
            } finally {
                fclose($handle);
            }
        }

        return response()->json(['schema_version' => 1, ...$input, 'records' => $records, 'native_write_authorized' => false])->header('Cache-Control', 'no-store, private');
    }
}
