<?php

declare(strict_types=1);

// Executed with governance's real locked production Composer dependencies.
// This tests the exact digest exception propagated by both approval boundaries,
// without needing database or a synthetic HTTP server.
require dirname(__DIR__, 2).'/services/governance/vendor/autoload.php';

use App\Domain\Approvals\BoundPlan;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\GovernanceLedger;

$binding = [
    'plan_id' => '550e8400-e29b-41d4-a716-446655440001',
    'revision' => 1,
    'tenant_id' => '550e8400-e29b-41d4-a716-446655440002',
    'action' => 'application.migrate',
    'site_id' => 'site-a',
    'environment' => 'development',
    'resource_id' => 'app-a',
    'requested_by' => '550e8400-e29b-41d4-a716-446655440003',
    'executor_ids' => ['550e8400-e29b-41d4-a716-446655440004'],
    'valid_until' => 1800000000,
];
$valid = $binding + ['digest' => GovernanceLedger::digest($binding)];
if (BoundPlan::fromArray($valid)->digest !== $valid['digest']) {
    throw new RuntimeException('Governance canonical approval digest rejected');
}
$bad = $binding + ['digest' => str_repeat('f', 64)];
try {
    BoundPlan::fromArray($bad);
    throw new RuntimeException('Governance invalid approval digest accepted');
} catch (IdentityDenied $error) {
    if ($error->status !== 409 || $error->reason !== 'plan_digest_mismatch') {
        throw new RuntimeException('Governance approval returned wrong 409 conflict', 0, $error);
    }
}
echo "Governance bound-plan digest mismatch: 409 PASS\n";
