<?php

declare(strict_types=1);

use App\Domain\Qualification\NativeQualification;

it('agrees with Planning on SHA-256 of canonical scopes, including UTF-8 and slashes', function (): void {
    $path = dirname(__DIR__, 4).'/contracts/fixtures/qualification-scope-digests-v1.json';
    $raw = file_get_contents($path);
    expect($raw)->toBeString();
    $vectors = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
    expect($vectors['schema_version'])->toBe(1)
        ->and($vectors['cases'])->toHaveCount(2);

    foreach ($vectors['cases'] as $vector) {
        $scope = $vector['scope'];
        expect(NativeQualification::digest($scope))->toBe($vector['sha256']);
        // Permuting object keys never changes scope identity.
        $permuted = array_reverse($scope, true);
        expect(NativeQualification::digest($permuted))->toBe($vector['sha256']);
    }
});

it('changes canonical scope identity for a different tenant, endpoint, and operation', function (): void {
    $path = dirname(__DIR__, 4).'/contracts/fixtures/qualification-scope-digests-v1.json';
    $vectors = json_decode(file_get_contents($path), true, 64, JSON_THROW_ON_ERROR);
    $scope = $vectors['cases'][0]['scope'];
    $base = NativeQualification::digest($scope);
    foreach (['tenant_id', 'site_id', 'endpoint_id', 'native_scope', 'method'] as $dimension) {
        $mutated = $scope;
        $mutated[$dimension] .= '-changed';
        expect(NativeQualification::digest($mutated))->not->toBe($base);
    }
});
