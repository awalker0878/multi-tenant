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
