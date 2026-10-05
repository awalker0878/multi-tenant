<?php

declare(strict_types=1);

use Illuminate\Support\Facades\DB;
use Opis\JsonSchema\Validator;

beforeEach(function (): void {
    initializeSupportFixture($this);
    $api = json_decode(file_get_contents(resource_path('contracts/governance-support-v1.json')), true);
    $this->validateSupport = function (string $name, array $body) use ($api): bool {
        $schema = json_decode(json_encode(['$schema' => 'https://json-schema.org/draft/2020-12/schema',
            '$ref' => '#/components/schemas/'.$name, 'components' => $api['components']]));

        return (new Validator)->validate(json_decode(json_encode($body)), $schema)->isValid();
    };
});

afterEach(function (): void {
    unlink($this->credentialFile);
});

it('matches the published support contract across creation decisions admission history review and role revocation', function (): void {
    expect(($this->validateSupport)('SecurityGrantStatus', $this->securityGrant))->toBeTrue();
    $request = createSupportRequest($this);
    expect(($this->validateSupport)('RequestCreated', $request))->toBeTrue();
    $request = approveSupportRequest($this, $request);
    expect(($this->validateSupport)('DecisionStatus', $request))->toBeTrue();
    $request = activateSupportRequest($this, $request);
    expect(($this->validateSupport)('ActiveStatus', $request))->toBeTrue();
    foreach ([['action' => 'support.membership.inspect', 'resource_id' => $this->targetMembership['id']],
        ['action' => 'support.grant.inspect', 'resource_id' => $this->targetGrant['id']]] as $resource) {
        $body = supportInspect($this, $request, $resource)->assertOk()->json();
        expect(($this->validateSupport)('DiagnosticResult', $body))->toBeTrue();
        $body['resource']['actor_id'] = $this->requesterId;
        expect(($this->validateSupport)('DiagnosticResult', $body))->toBeFalse();
    }
    $body = $this->getJson($this->supportPath.'/'.$request['id'])->assertOk()->json();
    expect(($this->validateSupport)('RequestStatus', $body))->toBeTrue();
    $body = $this->getJson($this->supportPath.'/'.$request['id'].'/audit')->assertOk()->json();
    expect(($this->validateSupport)('AuditPage', $body))->toBeTrue();
    $request = supportDecision($this, $request, 'revoke', $this->executor, ['reason_code' => 'incident_resolved', 'case_reference' => 'INC-100'])->assertOk()->json();
    expect(($this->validateSupport)('DecisionStatus', $request))->toBeTrue();
    $review = supportDecision($this, $request, 'review', $this->reviewer, ['outcome' => 'acceptable', 'case_reference' => 'REVIEW-104'])->assertOk()->json();
    expect(($this->validateSupport)('ReviewStatus', $review))->toBeTrue();
    $body = $this->getJson($this->supportPath.'/'.$request['id'])->assertOk()->json();
    expect(($this->validateSupport)('RequestStatus', $body))->toBeTrue();
    $body = $this->getJson($this->supportPath.'/'.$request['id'].'/audit')->assertOk()->json();
    expect(($this->validateSupport)('AuditPage', $body))->toBeTrue();
    $body = tenantCommand($this, '/v1/support-security-revocations', ['tenant_id' => $this->tenant, 'grant_id' => $this->securityGrant['id'],
        'revision' => 1, 'case_reference' => 'IAM-109', 'reason_code' => 'policy_review'], $this->installer)->assertOk()->json();
    expect(($this->validateSupport)('SecurityRevokeStatus', $body))->toBeTrue()
        ->and(DB::table('app.support_approvals')->count())->toBe(2);
});
