<?php

declare(strict_types=1);

// E2 verification of actual cryptography and domain predicates, no native qualification.
require __DIR__.'/../services/assurance/app/Domain/Qualification/CapabilityDefinitions.php';
require __DIR__.'/../services/assurance/app/Domain/Qualification/NativeQualification.php';

use App\Domain\Qualification\NativeQualification;

$fixture = json_decode(file_get_contents($argv[1]), true, 64, JSON_THROW_ON_ERROR);
$resolver = new NativeQualification;
$now = time();
$result = $resolver->resolve($fixture['bundle'], $fixture['keys'], $fixture['scope'], $now);
if ($result['verification']['valid'] !== true || $result['version'] !== 2) {
    throw new RuntimeException('signed_native_record_failed');
}
foreach (['unresolved', 'tampered', 'signature', 'foreign', 'expired', 'role', 'runtime', 'definition'] as $fault) {
    $bundle = $fixture['bundle'];
    $keys = $fixture['keys'];
    $scope = $fixture['scope'];
    if ($fault === 'unresolved') {
        $bundle['evidence'] = [];
    } elseif ($fault === 'tampered') {
        $bundle['evidence'][0]['content_base64'] = base64_encode('{}');
    } elseif ($fault === 'signature') {
        $bundle['evidence'][0]['signature_base64'] = base64_encode(str_repeat('x', 256));
    } elseif ($fault === 'foreign') {
        $scope['tenant_id'] = '00000000-0000-4000-8000-000000000001';
    } elseif ($fault === 'expired') {
        $keys['observer']['expires_at'] = $now;
    } elseif ($fault === 'role') {
        $keys['reviewer']['role'] = 'observer';
    } elseif ($fault === 'runtime') {
        $bundle['runtime'] = $bundle['evidence'][0];
    } else {
        $bundle['record']['scope']['artifacts']['adapter'] = str_repeat('f', 64);
    }
    try {
        $resolver->resolve($bundle, $keys, $scope, $now);
    } catch (RuntimeException) {
        continue;
    }
    throw new RuntimeException('unsafe_qualification_accepted:'.$fault);
}
echo "Native qualification cryptographic positive and eight negative controls passed (E2)\n";
