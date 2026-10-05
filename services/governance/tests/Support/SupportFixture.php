<?php

declare(strict_types=1);

use Illuminate\Support\Facades\DB;
use Illuminate\Testing\TestResponse;

function initializeSupportFixture(object $test): void
{
    initializeFederationFixture($test);
    $test->installer = federatedLogin($test, 'immutable-admin-subject');
    $test->token = $test->installer;
    $test->tenant = tenantCommand($test, '/v1/tenants', ['name' => 'Support tenant', 'administrator_subject' => 'support-tenant-owner'])->assertCreated()->json('id');
    $test->otherTenant = tenantCommand($test, '/v1/tenants', ['name' => 'Other tenant', 'administrator_subject' => 'other-owner'])->assertCreated()->json('id');
    $test->owner = federatedLogin($test, 'support-tenant-owner');
    $test->token = $test->owner;
    $test->scope = ['site_id' => 'site-a', 'environment' => 'production'];
    $test->requesterMembership = tenantMember($test, $test->tenant, 'support-requester', 'reader', $test->scope);
    $test->targetMembership = tenantMember($test, $test->tenant, 'affected-member', 'operator', $test->scope);
    $test->targetGrant = tenantCommand($test, '/v1/tenants/'.$test->tenant.'/grants', [
        'membership_id' => $test->targetMembership['id'], 'action' => 'application.write', 'site_id' => 'site-a',
        'environment' => 'production', 'resource_id' => 'application-a', 'expires_at' => now()->addHour()->toIso8601String(),
    ])->assertOk()->json();
    $test->requester = federatedLogin($test, 'support-requester');
    $test->executor = federatedLogin($test, 'support-executor');
    $test->security = federatedLogin($test, 'support-security');
    $test->reviewer = federatedLogin($test, 'support-reviewer');
    $actor = static fn (string $token): string => DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $token))->value('actor_id');
    $test->requesterId = $actor($test->requester);
    $test->executorId = $actor($test->executor);
    $test->securityId = $actor($test->security);
    $test->reviewerId = $actor($test->reviewer);
    $test->securityGrant = tenantCommand($test, '/v1/support-security-grants', $test->scope + [
        'tenant_id' => $test->tenant, 'actor_id' => $test->securityId, 'role' => 'approver',
        'expires_at' => now()->addDay()->toIso8601String(), 'case_reference' => 'IAM-100',
    ], $test->installer)->assertCreated()->json();
    $test->reviewGrant = tenantCommand($test, '/v1/support-security-grants', $test->scope + [
        'tenant_id' => $test->tenant, 'actor_id' => $test->reviewerId, 'role' => 'reviewer',
        'expires_at' => now()->addDay()->toIso8601String(), 'case_reference' => 'IAM-101',
    ], $test->installer)->assertCreated()->json();
    $test->supportInput = $test->scope + ['executor_id' => $test->executorId,
        'resources' => [['kind' => 'membership', 'id' => $test->targetMembership['id']], ['kind' => 'grant', 'id' => $test->targetGrant['id']]],
        'actions' => ['support.membership.inspect', 'support.grant.inspect'],
        'expires_at' => now()->addMinutes(10)->toIso8601String(), 'reason_code' => 'incident_diagnosis', 'case_reference' => 'INC-100'];
    $test->supportPath = '/v1/tenants/'.$test->tenant.'/support-access';
}

function createSupportRequest(object $test, array $overrides = [], ?string $key = null): array
{
    return tenantCommand($test, $test->supportPath, array_replace($test->supportInput, $overrides), $test->requester, $key)->assertCreated()->json();
}

function supportDecision(object $test, array $request, string $operation, string $token, array $extra = [], ?string $key = null): TestResponse
{
    return tenantCommand($test, $test->supportPath.'/'.$request['id'].'/'.$operation,
        ['revision' => $request['revision'], 'binding_sha256' => $request['binding_sha256']] + $extra, $token, $key);
}

function approveSupportRequest(object $test, ?array $request = null): array
{
    $request ??= createSupportRequest($test);
    $request = supportDecision($test, $request, 'approve', $test->owner, ['role' => 'tenant'])->assertOk()->assertJsonPath('state', 'requested')->json();

    return supportDecision($test, $request, 'approve', $test->security, ['role' => 'security'])->assertOk()->assertJsonPath('state', 'approved')->json();
}

function activateSupportRequest(object $test, ?array $request = null): array
{
    $request ??= approveSupportRequest($test);

    return supportDecision($test, $request, 'activate', $test->executor)->assertOk()->assertJsonPath('state', 'active')->json();
}

function supportInspect(object $test, array $request, array $changes = [], ?string $token = null): TestResponse
{
    return $test->withHeader('X-Console-Session', $token ?? $test->executor)->postJson($test->supportPath.'/'.$request['id'].'/inspect',
        array_replace($test->scope + ['binding_sha256' => $request['binding_sha256'], 'action' => 'support.membership.inspect', 'resource_id' => $test->targetMembership['id']], $changes));
}
