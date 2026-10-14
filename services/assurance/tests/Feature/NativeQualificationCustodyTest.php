<?php

declare(strict_types=1);

use App\Domain\Qualification\NativeQualification;

it('derives enrolled-key identity itself and refuses signed fingerprint impersonation', function (): void {
    $now = time();
    $private = openssl_pkey_new(['private_key_type' => OPENSSL_KEYTYPE_RSA, 'private_key_bits' => 2048]);
    expect($private)->not->toBeFalse();
    $details = openssl_pkey_get_details($private);
    expect($details)->toBeArray();
    $publicKey = $details['key'];
    $scope = [
        'tenant_id' => '10000000-0000-4000-8000-000000000001',
        'site_id' => '10000000-0000-4000-8000-000000000002',
        'endpoint_id' => '10000000-0000-4000-8000-000000000003',
    ];
    $keys = ['observer' => [
        'role' => 'observer',
        'revoked' => false,
        'subject_id' => 'independent-observer',
        'expires_at' => $now + 600,
        'public_key_pem' => $publicKey,
        'scope' => $scope,
    ]];
    $payload = [
        'subject_id' => 'independent-observer',
        'scope_sha256' => NativeQualification::digest($scope),
        'observed_at' => $now,
        'expires_at' => $now + 30,
    ];
    $sign = static function (array $claims) use ($private): array {
        $raw = json_encode($claims, JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);
        $signed = openssl_sign($raw, $signature, $private, OPENSSL_ALGO_SHA256);
        expect($signed)->toBeTrue();

        return [
            'key_id' => 'observer',
            'content_base64' => base64_encode($raw),
            'sha256' => hash('sha256', $raw),
            'signature_base64' => base64_encode($signature),
        ];
    };

    $method = new ReflectionMethod(NativeQualification::class, 'verify');
    $resolver = new NativeQualification;
    $verified = $method->invoke($resolver, $sign($payload), $keys, 'observer', $scope, $now);
    expect($verified['_key_sha256'])->toBe(hash('sha256', $publicKey));

    // The observer can validly sign a false fingerprint, but cannot use it
    // to impersonate the independent reviewer or receiving-owner key.
    $forged = $payload + ['_key_sha256' => hash('sha256', 'reviewer-public-key')];
    expect(fn () => $method->invoke($resolver, $sign($forged), $keys, 'observer', $scope, $now))
        ->toThrow(RuntimeException::class, 'evidence_reserved_field');
});

it('requires distinct readback evidence for each passed installed recovery method and mode', function (): void {
    $now = time();
    $scope = ['artifacts' => ['adapter' => str_repeat('a', 64)]];
    $matrix = [];
    $cases = ['adapter_behavior' => 'passed', 'installed_identity' => 'passed', 'runtime_artifacts' => 'passed'];
    foreach (\App\Domain\Qualification\CapabilityDefinitions::WIRE_METHODS as $name) {
        foreach (\App\Domain\Qualification\CapabilityDefinitions::MODES as $mode) {
            $key = 'method:'.$name.':'.$mode;
            $matrix[$key] = 'unsupported';
            $cases[$key] = 'unsupported';
        }
    }
    $method = \App\Domain\Qualification\CapabilityDefinitions::WIRE_METHODS[0];
    $other = \App\Domain\Qualification\CapabilityDefinitions::WIRE_METHODS[1];
    foreach ([$method, $other] as $name) {
        $key = 'method:'.$name.':rollback';
        $matrix[$key] = 'passed';
        $cases[$key] = 'passed';
    }
    $proof = [
        'kind' => 'native_conformance', 'simulation' => false, 'finalized' => true,
        'definition_sha256' => \App\Domain\Qualification\CapabilityDefinitions::SHA256,
        'runtime_artifacts' => $scope['artifacts'], 'observed_at' => $now,
        'cases' => $cases, 'method_modes' => $matrix,
        'snapshot' => ['recovery_measurements' => []],
    ];
    $check = new ReflectionMethod(NativeQualification::class, 'native');
    $resolver = new NativeQualification;
    expect(fn () => $check->invoke($resolver, $proof, $scope))
        ->toThrow(RuntimeException::class, 'native_recovery_readback_missing');

    $receipt = static fn (string $name, string $dataset): array => [
        'method' => $name, 'mode' => 'rollback', 'dataset_id' => $dataset,
        'sequence' => 1, 'observed_at' => $now,
        'scope_sha256' => NativeQualification::digest($scope),
        'artifacts' => $scope['artifacts'], 'readback_sha256' => str_repeat('d', 64),
        'outcome' => 'passed', 'consistency_passed' => true,
    ];
    $proof['snapshot']['recovery_measurements'] = [$receipt($method, 'dataset-one')];
    expect(fn () => $check->invoke($resolver, $proof, $scope))
        ->toThrow(RuntimeException::class, 'native_recovery_readback_missing');
    $proof['snapshot']['recovery_measurements'][] = $receipt($other, 'dataset-two');
    $check->invoke($resolver, $proof, $scope);
    $proof['snapshot']['recovery_measurements'][1]['scope_sha256'] = str_repeat('e', 64);
    expect(fn () => $check->invoke($resolver, $proof, $scope))
        ->toThrow(RuntimeException::class, 'native_recovery_readback_invalid');
});

it('rejects qualification records containing forged verifier-owned status', function (): void {
    $now = time();
    $scope = [
        'tenant_id' => '10000000-0000-4000-8000-000000000001',
        'site_id' => '10000000-0000-4000-8000-000000000002',
        'endpoint_id' => '10000000-0000-4000-8000-000000000003',
    ];
    $record = [
        'version' => 2, 'status' => 'qualified', 'revoked' => false,
        'evidence_level' => 'E3', 'expires_at' => $now + 60, 'scope' => $scope,
        'verification' => ['valid' => true, 'native_write_authorized' => true],
    ];
    expect(fn () => (new NativeQualification)->resolve(['record' => $record], [], $scope, $now))
        ->toThrow(RuntimeException::class, 'qualification_reserved_field');
});
