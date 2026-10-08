<?php

declare(strict_types=1);

namespace App\Domain\Qualification;

use RuntimeException;

/** Authenticated independent observations and decisions, never adapter declarations. */
final class NativeQualification
{
    /** @param array<string, mixed> $bundle
     * @param array<string, mixed> $keys
     * @param array<string, mixed> $scope
     * @return array<string, mixed> */
    public function resolve(array $bundle, array $keys, array $scope, int $now): array
    {
        $record = $bundle['record'] ?? [];
        $this->require(is_array($record) && ($record['version'] ?? null) === 2
            && ($record['status'] ?? null) === 'qualified' && ($record['revoked'] ?? null) === false
            && in_array($record['evidence_level'] ?? null, ['E3', 'E4'], true) && ($record['expires_at'] ?? 0) > $now
            && self::canonical($record['scope'] ?? null) === self::canonical($scope), 'qualification_unverified');
        $decision = $this->verify($bundle['decision'] ?? [], $keys, 'reviewer', $scope, $now);
        $this->require(($decision['kind'] ?? null) === 'qualification_decision'
            && ($decision['decision'] ?? null) === 'accepted_native'
            && ($decision['record_sha256'] ?? null) === self::digest($record)
            && ($decision['definition_sha256'] ?? null) === CapabilityDefinitions::SHA256
            && is_int($decision['revision'] ?? null) && $decision['revision'] > 0, 'qualification_decision_invalid');
        $proofs = $bundle['evidence'] ?? [];
        $this->require(is_array($proofs) && array_is_list($proofs) && count($proofs) >= 1 && count($proofs) <= 64, 'native_evidence_missing');
        $observed = [];
        $evidence = [];
        $observers = [];
        $observerKeys = [];
        $expiry = min($record['expires_at'], $decision['expires_at']);
        foreach ($proofs as $proof) {
            $receipt = $this->verify($proof, $keys, 'observer', $scope, $now);
            $this->native($receipt, $scope);
            $this->require(($receipt['adapter_conformant'] ?? null) === true, 'adapter_runtime_mismatch');
            $evidence[] = $proof['sha256'];
            $observers[] = $receipt['subject_id'];
            $observerKeys[] = $receipt['_key_sha256'];
            $expiry = min($expiry, $receipt['expires_at']);
            foreach (($receipt['capabilities'] ?? []) as $name => $capability) {
                $this->require(($receipt['cases']['capability:'.$name] ?? null) === 'passed', 'native_case_coverage_missing');
                $observed[$name][] = $capability;
            }
        }
        sort($evidence, SORT_STRING);
        $refs = $record['evidence_refs'] ?? [];
        sort($refs, SORT_STRING);
        $reviewed = $decision['evidence_sha256'] ?? [];
        sort($reviewed, SORT_STRING);
        $this->require($refs === $evidence && $reviewed === $evidence && count(array_unique($evidence)) === count($evidence), 'evidence_references_unresolved');
        $this->require(! in_array($decision['_key_sha256'], $observerKeys, true)
            && ! in_array($decision['subject_id'], $observers, true)
            && $decision['subject_id'] !== ($decision['requested_by'] ?? null), 'independent_reviewer_required');
        // Runtime evidence is separately refreshed. A later pass cannot re-sign a decision.
        $runtime = $this->verify($bundle['runtime'] ?? [], $keys, 'observer', $scope, $now);
        $this->native($runtime, $scope);
        $this->require($now - $runtime['observed_at'] <= 60
            && $runtime['expires_at'] <= $runtime['observed_at'] + 120, 'runtime_observation_stale');
        $this->require(($runtime['adapter_conformant'] ?? null) === true, 'adapter_runtime_mismatch');
        $this->require(($runtime['decision_sha256'] ?? null) === $bundle['decision']['sha256'], 'runtime_decision_unbound');
        $expiry = min($expiry, $runtime['expires_at']);
        $this->require(($record['dimensions'] ?? []) === ($runtime['dimensions'] ?? null), 'runtime_dimensions_changed');
        foreach ($record['dimensions'] as $dimension) {
            $this->require(($runtime['cases']['dimension:'.$dimension] ?? null) === 'passed', 'native_dimension_unverified');
        }
        foreach (($record['capabilities'] ?? []) as $name => $capability) {
            $this->require(isset($observed[$name]) && ($capability['status'] ?? null) === 'supported'
                && ($capability['expires_at'] ?? 0) > $now
                && ($runtime['cases']['capability:'.$name] ?? null) === 'passed'
                && isset($runtime['capabilities'][$name]), 'native_capability_unverified');
            // Reviewed values must be evidenced. Runtime bounds cannot drift from the review.
            $this->require(count(array_filter($observed[$name], fn (array $row): bool => self::canonical($row['values'] ?? null) === self::canonical($capability['values'] ?? null))) >= 1
                && self::canonical($runtime['capabilities'][$name]['values'] ?? null) === self::canonical($capability['values'] ?? null), 'native_capability_changed');
        }

        if ($record['evidence_level'] === 'E4') {
            $acceptance = $this->verify($bundle['acceptance'] ?? [], $keys, 'receiver', $scope, $now);
            $this->require(($acceptance['kind'] ?? null) === 'operating_acceptance'
                && ($acceptance['decision'] ?? null) === 'accepted'
                && ($acceptance['revoked'] ?? null) === false
                && ($acceptance['qualification_sha256'] ?? null) === $bundle['decision']['sha256']
                && ($acceptance['record_sha256'] ?? null) === self::digest($record)
                && ($acceptance['definition_sha256'] ?? null) === CapabilityDefinitions::SHA256
                && $acceptance['_key_sha256'] !== $decision['_key_sha256']
                && ! in_array($acceptance['_key_sha256'], $observerKeys, true)
                && $acceptance['subject_id'] !== $decision['subject_id']
                && ! in_array($acceptance['subject_id'], $observers, true),
                'independent_receiving_acceptance_required');
            $expiry = min($expiry, $acceptance['expires_at']);
        }

        return $record + ['verification' => ['valid' => true, 'definition_sha256' => CapabilityDefinitions::SHA256,
            'decision_sha256' => $bundle['decision']['sha256'], 'runtime_sha256' => $bundle['runtime']['sha256'],
            'record_sha256' => self::digest($record), 'resolved_at' => $now, 'expires_at' => $expiry,
            'acceptance_sha256' => $record['evidence_level'] === 'E4' ? $bundle['acceptance']['sha256'] : null]];
    }

    /** @param array<string, mixed> $value
     * @param array<string, mixed> $keys
     * @param array<string, mixed> $scope
     * @return array<string, mixed> */
    private function verify(array $value, array $keys, string $role, array $scope, int $now): array
    {
        $key = $keys[$value['key_id'] ?? ''] ?? null;
        $this->require(is_array($key) && ($key['role'] ?? null) === $role && ($key['expires_at'] ?? 0) > $now
            && ($key['revoked'] ?? false) === false, 'evidence_key_unenrolled');
        foreach (['tenant_id', 'site_id', 'endpoint_id'] as $field) {
            $this->require(($key['scope'][$field] ?? null) === ($scope[$field] ?? null), 'evidence_key_scope_denied');
        }
        $raw = base64_decode($value['content_base64'] ?? '', true);
        $signature = base64_decode($value['signature_base64'] ?? '', true);
        $this->require(is_string($raw) && strlen($raw) <= 262144 && is_string($signature)
            && ($value['sha256'] ?? null) === hash('sha256', $raw), 'evidence_custody_tampered');
        $public = openssl_pkey_get_public($key['public_key_pem']);
        $this->require($public !== false, 'evidence_key_invalid');
        $details = openssl_pkey_get_details($public);
        $this->require(is_array($details) && $details['type'] === OPENSSL_KEYTYPE_RSA && $details['bits'] >= 2048, 'evidence_key_invalid');
        $this->require(openssl_verify($raw, $signature, $public, OPENSSL_ALGO_SHA256) === 1, 'evidence_signature_invalid');
        $receipt = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
        $this->require(is_array($receipt) && ($receipt['subject_id'] ?? null) === $key['subject_id']
            && ($receipt['scope_sha256'] ?? null) === self::digest($scope)
            && is_int($receipt['observed_at'] ?? null) && $receipt['observed_at'] <= $now
            && ($receipt['expires_at'] ?? 0) > $now && $receipt['expires_at'] <= $key['expires_at'], 'evidence_scope_or_freshness_invalid');

        return $receipt + ['_key_sha256' => hash('sha256', $details['key'])];
    }

    /** @param array<string, mixed> $receipt
     * @param array<string, mixed> $scope */
    private function native(array $receipt, array $scope): void
    {
        $this->require(($receipt['kind'] ?? null) === 'native_conformance'
            && ($receipt['simulation'] ?? null) === false && ($receipt['finalized'] ?? null) === true
            && ($receipt['definition_sha256'] ?? null) === CapabilityDefinitions::SHA256
            && self::canonical($receipt['runtime_artifacts'] ?? null) === self::canonical($scope['artifacts'] ?? null)
            && ($receipt['cases']['adapter_behavior'] ?? null) === 'passed'
            && ($receipt['cases']['installed_identity'] ?? null) === 'passed'
            && ($receipt['cases']['runtime_artifacts'] ?? null) === 'passed', 'native_evidence_required');
    }

    public static function digest(mixed $value): string
    {
        return hash('sha256', self::canonical($value));
    }

    public static function canonical(mixed $value): string
    {
        $normalize = function (mixed $row) use (&$normalize): mixed {
            if (! is_array($row)) {
                return $row;
            }
            if (! array_is_list($row)) {
                ksort($row, SORT_STRING);
            }

            return array_map($normalize, $row);
        };

        return json_encode($normalize($value), JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
    }

    /** @phpstan-assert true $condition */
    private function require(bool $condition, string $reason): void
    {
        if (! $condition) {
            throw new RuntimeException($reason);
        }
    }
}
