<?php

declare(strict_types=1);

namespace App\Application\Qualification\Actions;

use App\Domain\Qualification\NativeQualification;
use Throwable;

final class ResolveQualification
{
    /** @param array<string, mixed> $scope
     * @return array<string, mixed> */
    public function handle(array $scope): array
    {
        $path = config('planning.qualification_registry_file');
        $unknown = ['id' => null, 'version' => 2, 'status' => 'unknown', 'scope' => $scope,
            'evidence_level' => null, 'expires_at' => 0, 'revoked' => false, 'evidence_refs' => [],
            'dimensions' => [], 'capabilities' => (object) [], 'verification' => null];
        if ($path === null) {
            return $unknown;
        }
        $registry = $this->read($path);
        // Legacy import is explicitly unverified, even when it says E3 and qualified.
        if (($registry['schema_version'] ?? null) === 1) {
            $legacy = array_filter($registry['records'] ?? [], fn (array $row): bool => NativeQualification::canonical($row['scope'] ?? null) === NativeQualification::canonical($scope));
            abort_if(count($legacy) > 1, 503, 'qualification_conflict');

            return $unknown;
        }
        abort_unless(($registry['schema_version'] ?? null) === 2 && is_array($registry['records'] ?? null), 503);
        $records = array_values(array_filter($registry['records'], fn (array $row): bool => NativeQualification::canonical($row['record']['scope'] ?? null) === NativeQualification::canonical($scope)));
        abort_if(count($records) > 1, 503, 'qualification_conflict');
        if ($records === []) {
            return $unknown;
        }
        $trust = $this->read(config('planning.qualification_trust_file'));
        abort_unless(($trust['schema_version'] ?? null) === 1 && is_array($trust['keys'] ?? null), 503);
        $runtime = $this->read(config('planning.qualification_runtime_file'));
        abort_unless(($runtime['schema_version'] ?? null) === 1, 503);
        $decision = $records[0]['decision']['sha256'] ?? '';
        $records[0]['runtime'] = $runtime['records'][$decision] ?? [];
        try {
            return (new NativeQualification)->resolve($records[0], $trust['keys'], $scope, time());
        } catch (Throwable) {
            return $unknown;
        }
    }

    /** @return array<string, mixed> */
    private function read(mixed $path): array
    {
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
            $data = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
            abort_unless(is_array($data), 503);

            return $data;
        } catch (Throwable) {
            abort(503, 'qualification_custody_unavailable');
        } finally {
            fclose($handle);
        }
    }
}
