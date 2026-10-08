<?php

declare(strict_types=1);

// E2 protocol controls; a synthetic receiving signature does not establish E4.
require __DIR__.'/../services/assurance/app/Domain/Qualification/CapabilityDefinitions.php';
require __DIR__.'/../services/assurance/app/Domain/Qualification/NativeQualification.php';

use App\Domain\Qualification\NativeQualification;

$fixture = json_decode(file_get_contents($argv[1]), true, 64, JSON_THROW_ON_ERROR);
$resolver = new NativeQualification;
$resolved = $resolver->resolve($fixture['bundle'], $fixture['keys'], $fixture['scope'], time());
if ($resolved['evidence_level'] !== 'E4' || $resolved['verification']['valid'] !== true) {
    throw new RuntimeException('receiving_signature_control_failed');
}
foreach (['missing', 'wrong_role', 'unbound'] as $fault) {
    $bundle = $fixture['bundle'];
    $keys = $fixture['keys'];
    if ($fault === 'missing') {
        unset($bundle['acceptance']);
    } elseif ($fault === 'wrong_role') {
        $keys['receiver']['role'] = 'reviewer';
    } else {
        $bundle['acceptance'] = $bundle['decision'];
    }
    try {
        $resolver->resolve($bundle, $keys, $fixture['scope'], time());
    } catch (RuntimeException) {
        continue;
    }
    throw new RuntimeException('unsafe_receiving_accepted:'.$fault);
}
echo "Independent receiving signature controls passed (E2)\n";
