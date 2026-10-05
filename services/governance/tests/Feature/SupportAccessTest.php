<?php

declare(strict_types=1);

use App\Application\Support\Actions\ExpireSupportAccess;
use App\Application\Support\Actions\ReadSupportAccess;
use App\Application\Support\Contracts\SupportTrust;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportTrustState;
use Firebase\JWT\JWT;
use Illuminate\Database\QueryException;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

beforeEach(function (): void {
    initializeSupportFixture($this);
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

it('requires dual independent approval and executor activation before scoped diagnostic access', function (): void {
    $request = createSupportRequest($this);
    supportInspect($this, $request)->assertForbidden();
    supportDecision($this, $request, 'activate', $this->executor)->assertForbidden();
    $first = supportDecision($this, $request, 'approve', $this->owner, ['role' => 'tenant'])->assertOk()->json();
    supportDecision($this, $first, 'activate', $this->executor)->assertForbidden();
    $approved = supportDecision($this, $first, 'approve', $this->security, ['role' => 'security'])->assertOk()->json();
    supportInspect($this, $approved)->assertForbidden();
    $active = activateSupportRequest($this, $approved);
    $result = supportInspect($this, $active)->assertOk()->assertHeader('Cache-Control', 'no-store, private')
        ->assertJsonPath('resource.id', $this->targetMembership['id'])->assertJsonPath('resource.role', 'operator')
        ->assertJsonPath('authority_use', 'diagnostic_result_only')->json();
    expect($result['resource'])->not->toHaveKeys(['actor_id', 'subject', 'session_hash', 'password_hash']);
    supportInspect($this, $active, ['action' => 'support.grant.inspect', 'resource_id' => $this->targetGrant['id']])
        ->assertOk()->assertJsonPath('resource.action', 'application.write');
    $this->withHeader('X-Console-Session', $this->executor)->getJson('/v1/tenants/'.$this->tenant.'/memberships')->assertNotFound();
    $this->getJson('/v1/tenants/'.$this->otherTenant)->assertNotFound();
    expect(DB::table('app.support_audit')->where('event', 'support.access.admitted')->count())->toBe(2)
        ->and(DB::table('app.support_requests')->value('admission_count'))->toBe(2)
        ->and(DB::table('app.support_audit')->count())->toBe(DB::table('app.support_outbox')->count());
});

it('rejects body privilege injection unsupported actions wildcards and duplicate resources', function (string $fault): void {
    $input = $this->supportInput;
    match ($fault) {
        'actor' => $input['requester_id'] = $this->securityId,
        'state' => $input['state'] = 'active',
        'scope' => $input['site_id'] = '*',
        'action' => $input['actions'] = ['support.impersonate'],
        'resource-field' => $input['resources'][0]['tenant_id'] = $this->otherTenant,
        'duplicate' => $input['resources'][] = $input['resources'][0],
    };
    tenantCommand($this, $this->supportPath, $input, $this->requester)->assertStatus(422);
    expect(DB::table('app.support_requests')->count())->toBe(0);
})->with(['actor', 'state', 'scope', 'action', 'resource-field', 'duplicate']);

it('lets neither requester executor nor one person supply both approval roles', function (): void {
    $request = createSupportRequest($this);
    supportDecision($this, $request, 'approve', $this->requester, ['role' => 'tenant'])->assertForbidden();
    supportDecision($this, $request, 'approve', $this->executor, ['role' => 'security'])->assertForbidden();
    $ownerId = DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $this->owner))->value('actor_id');
    tenantCommand($this, '/v1/support-security-grants', $this->scope + ['tenant_id' => $this->tenant, 'actor_id' => $ownerId,
        'role' => 'approver', 'expires_at' => now()->addDay()->toIso8601String(), 'case_reference' => 'IAM-102'], $this->installer)->assertCreated();
    $request = supportDecision($this, $request, 'approve', $this->owner, ['role' => 'tenant'])->assertOk()->json();
    supportDecision($this, $request, 'approve', $this->owner, ['role' => 'security'])->assertForbidden()->assertJsonPath('error', 'independent_approver_required');
    expect(DB::table('app.support_approvals')->count())->toBe(1);
});

it('cannot appoint security authority through tenant administration or self assignment', function (): void {
    $input = $this->scope + ['tenant_id' => $this->tenant, 'actor_id' => $this->executorId, 'role' => 'approver',
        'expires_at' => now()->addDay()->toIso8601String(), 'case_reference' => 'IAM-103'];
    tenantCommand($this, '/v1/support-security-grants', $input, $this->owner)->assertForbidden();
    $input['actor_id'] = DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $this->installer))->value('actor_id');
    tenantCommand($this, '/v1/support-security-grants', $input, $this->installer)->assertForbidden();
    expect(DB::table('app.support_security_grants')->count())->toBe(2);
});

it('denies changed digest tenant action site environment and resource scope without disclosure', function (string $field): void {
    $request = activateSupportRequest($this);
    $changes = match ($field) {
        'digest' => ['binding_sha256' => str_repeat('0', 64)],
        'site' => ['site_id' => 'site-b'], 'environment' => ['environment' => 'development'],
        'resource' => ['resource_id' => (string) Str::uuid()],
        'kind' => ['action' => 'support.grant.inspect'],
    };
    supportInspect($this, $request, $changes)->assertForbidden();
    $this->getJson('/v1/tenants/'.$this->otherTenant.'/support-access/'.$request['id'])->assertNotFound();
    expect(DB::table('app.support_requests')->value('admission_count'))->toBe(0)
        ->and(DB::table('app.support_audit')->where('event', 'support.access.denied')->count())->toBe(1);
})->with(['digest', 'site', 'environment', 'resource', 'kind']);

it('requires resources to belong to the exact tenant site and environment at independent approval', function (): void {
    $request = createSupportRequest($this, ['resources' => [['kind' => 'membership', 'id' => (string) Str::uuid()]], 'actions' => ['support.membership.inspect']]);
    supportDecision($this, $request, 'approve', $this->owner, ['role' => 'tenant'])->assertStatus(409);
    expect(DB::table('app.support_approvals')->count())->toBe(0);
    $outside = tenantMember($this, $this->tenant, 'outside-member', 'reader', ['site_id' => 'site-b', 'environment' => 'production']);
    $request = createSupportRequest($this, ['resources' => [['kind' => 'membership', 'id' => $outside['id']]], 'actions' => ['support.membership.inspect']]);
    supportDecision($this, $request, 'approve', $this->owner, ['role' => 'tenant'])->assertStatus(409);
});

it('enforces request and decision idempotency after rechecking current authority', function (): void {
    $request = createSupportRequest($this, key: 'request-stable-key');
    expect(createSupportRequest($this, key: 'request-stable-key'))->toBe($request);
    tenantCommand($this, $this->supportPath, array_replace($this->supportInput, ['case_reference' => 'INC-changed']), $this->requester, 'request-stable-key')->assertStatus(409);
    $first = supportDecision($this, $request, 'approve', $this->owner, ['role' => 'tenant'], 'decision-stable-key')->assertOk()->json();
    supportDecision($this, $request, 'approve', $this->owner, ['role' => 'tenant'], 'decision-stable-key')->assertOk()->assertExactJson($first);
    supportDecision($this, $request, 'approve', $this->security, ['role' => 'security'])->assertStatus(409);
    expect(DB::table('app.support_requests')->count())->toBe(1)->and(DB::table('app.support_approvals')->count())->toBe(1);
});

it('makes expiry effective exactly at the deadline and records one immutable expiry fact', function (): void {
    $request = activateSupportRequest($this);
    $this->travelTo(Carbon::parse($request['effective_until']));
    supportInspect($this, $request)->assertStatus(409);
    expect(app(ExpireSupportAccess::class)->handle())->toBe(0)
        ->and(DB::table('app.support_requests')->value('state'))->toBe('expired')
        ->and(DB::table('app.support_audit')->where('event', 'support.access.expired')->count())->toBe(1);
});

it('bounds lifetime to one hour and to the initiating session and denies silent session renewal', function (): void {
    tenantCommand($this, $this->supportPath, array_replace($this->supportInput, ['expires_at' => now()->addMinutes(61)->toIso8601String()]), $this->requester)->assertStatus(422);
    $request = createSupportRequest($this, ['expires_at' => now()->addMinutes(59)->toIso8601String()]);
    $sessionEnd = DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $this->requester))->value('expires_at');
    expect(strtotime($request['binding']['expires_at']))->toBe(strtotime($sessionEnd));
    $request = activateSupportRequest($this, approveSupportRequest($this, $request));
    $otherSession = federatedLogin($this, 'support-executor');
    supportInspect($this, $request, token: $otherSession)->assertForbidden()->assertJsonPath('error', 'support_session_mismatch');
});

it('permanently invalidates a request after requester approver or executor authority changes', function (string $change): void {
    $request = activateSupportRequest($this);
    if ($change === 'requester') {
        tenantMember($this, $this->tenant, 'support-requester', 'reader', $this->scope, 1, 'revoked');
        tenantMember($this, $this->tenant, 'support-requester', 'reader', $this->scope, 2);
    } elseif ($change === 'security') {
        tenantCommand($this, '/v1/support-security-revocations', ['tenant_id' => $this->tenant, 'grant_id' => $this->securityGrant['id'],
            'revision' => 1, 'case_reference' => 'IAM-104', 'reason_code' => 'suspected_compromise'], $this->installer)->assertOk();
    } elseif ($change === 'owner-session') {
        $this->withHeader('X-Console-Session', $this->owner)->postJson('/identity/logout')->assertOk()->assertJsonPath('status', 'signed_out');
    } else {
        tenantMember($this, $this->tenant, 'affected-member', 'reader', $this->scope, 1);
    }
    supportInspect($this, $request)->assertForbidden()->assertJsonPath('error', 'support_authority_changed');
    expect(DB::table('app.support_requests')->value('state'))->toBe('invalidated');
    supportInspect($this, $request)->assertStatus(409);
})->with(['requester', 'security', 'owner-session', 'resource']);

it('rejects disabled executors at authentication before any diagnostic data is read', function (): void {
    $request = activateSupportRequest($this);
    DB::table('app.federated_actors')->where('id', $this->executorId)->update(['disabled_at' => now()]);
    supportInspect($this, $request)->assertUnauthorized();
    expect(DB::table('app.support_requests')->value('admission_count'))->toBe(0);
});

it('denies signing-key removal before ordinary session expiry and retains the invalidation', function (): void {
    $request = activateSupportRequest($this);
    $key = openssl_pkey_new(['private_key_bits' => 2048, 'private_key_type' => OPENSSL_KEYTYPE_RSA]);
    $details = openssl_pkey_get_details($key);
    $this->provider->keyOverride = [['kty' => 'RSA', 'use' => 'sig', 'alg' => 'RS256', 'kid' => 'replacement',
        'n' => JWT::urlsafeB64Encode($details['rsa']['n']), 'e' => JWT::urlsafeB64Encode($details['rsa']['e'])]];
    supportInspect($this, $request)->assertForbidden();
    expect(DB::table('app.support_requests')->value('state'))->toBe('invalidated');
    $this->provider->keyOverride = null;
    supportInspect($this, $request)->assertStatus(409);
});

it('holds support access on issuer or key-custody loss but still permits explicit revocation', function (string $failure): void {
    $request = activateSupportRequest($this);
    if ($failure === 'issuer') {
        $this->provider->unavailable = true;
    } else {
        DB::table('app.identity_secrets')->update(['ciphertext' => 'missing-key-custody']);
    }
    supportInspect($this, $request)->assertStatus(503)->assertJsonPath('error', 'support_trust_unavailable');
    expect(DB::table('app.support_audit')->where('event', 'support.access.denied')->count())->toBe(1);
    supportDecision($this, $request, 'revoke', $this->requester, ['reason_code' => 'suspected_compromise', 'case_reference' => 'INC-100'])->assertOk();
    expect(DB::table('app.support_requests')->value('state'))->toBe('revoked');
})->with(['issuer', 'custody']);

it('holds every support entrypoint under changed recovery custody without rebind', function (): void {
    $request = activateSupportRequest($this);
    $before = DB::table('app.identity_admission')->value('binding_sha256');
    $this->admission['epoch'] = bin2hex(random_bytes(32));
    file_put_contents($this->admissionFile, json_encode($this->admission));
    supportInspect($this, $request)->assertStatus(503)->assertJsonPath('error', 'identity_recovery_required');
    $this->getJson($this->supportPath.'/'.$request['id'])->assertStatus(503);
    expect(DB::table('app.identity_admission')->value('binding_sha256'))->toBe($before)
        ->and(DB::table('app.support_requests')->value('admission_count'))->toBe(0);
});

it('requires independent post-use review and preserves immutable auditable decisions', function (): void {
    $request = activateSupportRequest($this);
    supportInspect($this, $request)->assertOk();
    $request = supportDecision($this, $request, 'revoke', $this->executor, ['reason_code' => 'incident_resolved', 'case_reference' => 'INC-100'])->assertOk()->json();
    $review = ['outcome' => 'acceptable', 'case_reference' => 'REVIEW-100'];
    supportDecision($this, $request, 'review', $this->security, $review)->assertForbidden();
    supportDecision($this, $request, 'review', $this->executor, $review)->assertForbidden();
    supportDecision($this, $request, 'review', $this->reviewer, $review, 'review-stable-key')->assertOk()->assertJsonPath('reviewed', true);
    supportDecision($this, $request, 'review', $this->reviewer, $review, 'review-stable-key')->assertOk();
    supportDecision($this, $request, 'review', $this->reviewer, $review)->assertStatus(409);
    $body = $this->withHeader('X-Console-Session', $this->reviewer)->getJson($this->supportPath.'/'.$request['id'].'/audit')->assertOk()->json();
    expect(array_column($body['events'], 'event'))->toContain('support.access.requested', 'support.access.approved', 'support.access.activated', 'support.access.admitted', 'support.access.revoked', 'support.access.reviewed')
        ->and(json_encode($body))->not->toContain($this->executor, $this->temporary, 'synthetic-oidc-secret', 'session_hash', 'console_fingerprint')
        ->and(DB::table('app.support_reviews')->count())->toBe(1);
});

it('rolls back protected data admission if its audit outbox cannot commit', function (): void {
    $request = activateSupportRequest($this);
    $this->withoutExceptionHandling();
    DB::statement('DROP TABLE app.support_outbox');
    $before = DB::table('app.support_audit')->count();
    expect(fn () => supportInspect($this, $request))->toThrow(QueryException::class);
    expect(DB::table('app.support_requests')->value('admission_count'))->toBe(0)
        ->and(DB::table('app.support_audit')->count())->toBe($before);
});

it('requires ownership of the commit boundary before returning protected results', function (): void {
    $request = createSupportRequest($this);
    DB::beginTransaction();
    try {
        expect(fn () => app(ReadSupportAccess::class)->handle($this->requester, $this->workload, $this->tenant, $request['id']))->toThrow(IdentityDenied::class);
    } finally {
        DB::rollBack();
    }
});

it('denies self approval even when the named requester or executor has valid security authority', function (string $person): void {
    $actor = $person === 'requester' ? $this->requesterId : $this->executorId;
    $token = $person === 'requester' ? $this->requester : $this->executor;
    tenantCommand($this, '/v1/support-security-grants', $this->scope + ['tenant_id' => $this->tenant, 'actor_id' => $actor,
        'role' => 'approver', 'expires_at' => now()->addDay()->toIso8601String(), 'case_reference' => 'IAM-105'], $this->installer)->assertCreated();
    $request = createSupportRequest($this);
    supportDecision($this, $request, 'approve', $token, ['role' => 'security'])->assertForbidden()->assertJsonPath('error', 'independent_approver_required');
    expect(DB::table('app.support_approvals')->count())->toBe(0);
})->with(['requester', 'executor']);

it('denies an approving actor post-use review even if separately assigned the reviewer role', function (): void {
    tenantCommand($this, '/v1/support-security-grants', $this->scope + ['tenant_id' => $this->tenant, 'actor_id' => $this->securityId,
        'role' => 'reviewer', 'expires_at' => now()->addDay()->toIso8601String(), 'case_reference' => 'IAM-106'], $this->installer)->assertCreated();
    $request = activateSupportRequest($this);
    supportInspect($this, $request)->assertOk();
    $request = supportDecision($this, $request, 'revoke', $this->executor, ['reason_code' => 'incident_resolved', 'case_reference' => 'INC-100'])->assertOk()->json();
    supportDecision($this, $request, 'review', $this->security, ['outcome' => 'acceptable', 'case_reference' => 'REVIEW-101'])
        ->assertForbidden()->assertJsonPath('error', 'independent_approver_required');
    expect(DB::table('app.support_reviews')->count())->toBe(0);
});

it('refuses new privileges from stale or legacy sessions while preserving ordinary session behavior', function (): void {
    DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $this->requester))->update(['provider_key_sha256' => null]);
    $this->withHeader('X-Console-Session', $this->requester)->getJson('/v1/tenants/'.$this->tenant)->assertOk();
    tenantCommand($this, $this->supportPath, $this->supportInput, $this->requester)->assertForbidden();
    $this->requester = federatedLogin($this, 'support-requester');
    $request = createSupportRequest($this);
    $this->travel(5)->minutes();
    supportDecision($this, $request, 'approve', $this->owner, ['role' => 'tenant'])->assertForbidden()->assertJsonPath('error', 'support_reauthentication_required');
    expect(DB::table('app.support_approvals')->count())->toBe(0);
});

it('invalidates after tenant restoration or Console credential rotation instead of reviving old access', function (string $change): void {
    $request = activateSupportRequest($this);
    if ($change === 'tenant') {
        tenantCommand($this, '/v1/tenants/'.$this->tenant.'/state', ['revision' => 1, 'state' => 'suspended'], $this->owner)->assertOk();
        tenantCommand($this, '/v1/tenants/'.$this->tenant.'/state', ['revision' => 2, 'state' => 'active'], $this->owner)->assertOk();
    } else {
        $replacement = bin2hex(random_bytes(32));
        file_put_contents($this->credentialFile, $replacement);
        supportInspect($this, $request)->assertUnauthorized();
        $this->withHeader('Authorization', 'Bearer '.$replacement);
    }
    supportInspect($this, $request)->assertForbidden()->assertJsonPath('error', 'support_authority_changed');
    expect(DB::table('app.support_requests')->value('state'))->toBe('invalidated');
})->with(['tenant', 'credential']);

it('requires a security role matching the tenant site and environment', function (): void {
    $request = createSupportRequest($this);
    // A distinct explicit assignment cannot widen the original security grant.
    $stranger = federatedLogin($this, 'different-site-security');
    $actor = DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $stranger))->value('actor_id');
    tenantCommand($this, '/v1/support-security-grants', ['site_id' => 'site-b', 'environment' => 'production',
        'tenant_id' => $this->tenant, 'actor_id' => $actor, 'role' => 'approver',
        'expires_at' => now()->addDay()->toIso8601String(), 'case_reference' => 'IAM-107'], $this->installer)->assertCreated();
    supportDecision($this, $request, 'approve', $stranger, ['role' => 'security'])->assertNotFound();
    $this->withHeader('X-Console-Session', $this->security)->getJson('/v1/tenants/'.$this->otherTenant.'/support-access/'.$request['id'])->assertNotFound();
});

it('keeps invalidation durable after the attributed denial budget is exhausted', function (): void {
    $request = activateSupportRequest($this);
    for ($i = 0; $i < 60; $i++) {
        supportInspect($this, $request, ['site_id' => 'wrong-site'])->assertForbidden();
    }
    tenantMember($this, $this->tenant, 'affected-member', 'reader', $this->scope, 1);
    supportInspect($this, $request)->assertStatus(429);
    expect(DB::table('app.support_requests')->value('state'))->toBe('invalidated')
        ->and(DB::table('app.support_audit')->where('event', 'support.access.denied')->count())->toBe(60)
        ->and(DB::table('app.support_audit')->where('event', 'support.access.invalidated')->count())->toBe(1);
});

it('reauthorizes every audit page and rejects cross-request positions', function (): void {
    $request = activateSupportRequest($this);
    for ($i = 0; $i < 101; $i++) {
        supportInspect($this, $request)->assertOk();
    }
    $page = $this->withHeader('X-Console-Session', $this->reviewer)->getJson($this->supportPath.'/'.$request['id'].'/audit')->assertOk()->json();
    expect($page['events'])->toHaveCount(100)->and($page['next_before'])->not->toBeNull();
    $next = $this->getJson($this->supportPath.'/'.$request['id'].'/audit?before='.$page['next_before'])->assertOk()->json();
    expect(array_intersect(array_column($page['events'], 'id'), array_column($next['events'], 'id')))->toBe([])
        ->and($next['next_before'])->toBeNull();
    $foreign = DB::table('app.support_audit')->where('event', 'support.security.granted')->value('id');
    $this->getJson($this->supportPath.'/'.$request['id'].'/audit?before='.$foreign)->assertNotFound();
    tenantCommand($this, '/v1/support-security-revocations', ['tenant_id' => $this->tenant, 'grant_id' => $this->reviewGrant['id'],
        'revision' => 1, 'case_reference' => 'IAM-108', 'reason_code' => 'policy_review'], $this->installer)->assertOk();
    $this->withHeader('X-Console-Session', $this->reviewer)->getJson($this->supportPath.'/'.$request['id'].'/audit?before='.$page['next_before'])->assertNotFound();
    $this->withHeader('X-Console-Session', $this->installer)->getJson($this->supportPath.'/'.$request['id'].'/audit')->assertNotFound();
});

it('blocks another activation until an overdue used request receives independent review', function (): void {
    $old = activateSupportRequest($this);
    supportInspect($this, $old)->assertOk();
    $old = supportDecision($this, $old, 'revoke', $this->executor, ['reason_code' => 'incident_resolved', 'case_reference' => 'INC-100'])->assertOk()->json();
    // Disposable owner fixture: represent a previously used terminal record whose review deadline passed.
    DB::table('app.support_requests')->where('id', $old['id'])->update(['effective_until' => now()->subHours(25)]);
    $next = approveSupportRequest($this);
    supportDecision($this, $next, 'activate', $this->executor)->assertForbidden()->assertJsonPath('error', 'support_review_required');
    supportDecision($this, $old, 'review', $this->reviewer, ['outcome' => 'acceptable', 'case_reference' => 'REVIEW-102'])->assertOk();
    activateSupportRequest($this, $next);
});

it('retains nonempty terminal support history for recovery qualification', function (): void {
    $request = activateSupportRequest($this);
    supportInspect($this, $request)->assertOk();
    $request = supportDecision($this, $request, 'revoke', $this->executor, ['reason_code' => 'incident_resolved', 'case_reference' => 'INC-100'])->assertOk()->json();
    supportDecision($this, $request, 'review', $this->reviewer, ['outcome' => 'acceptable', 'case_reference' => 'REVIEW-103'])->assertOk();
    supportInspect($this, $request)->assertStatus(409);
    expect(DB::table('app.support_requests')->value('state'))->toBe('revoked')
        ->and(DB::table('app.support_requests')->value('admission_count'))->toBe(1)
        ->and(DB::table('app.support_approvals')->count())->toBe(2)
        ->and(DB::table('app.support_reviews')->count())->toBe(1)
        ->and(DB::table('app.support_audit')->where('resource_id', $request['id'])->count())->toBe(8)
        ->and(DB::table('app.support_audit')->count())->toBe(DB::table('app.support_outbox')->count());
});

it('rechecks the presented Console workload after remote trust verification before issuing any privilege', function (): void {
    $delegate = app(SupportTrust::class);
    $file = $this->credentialFile;
    app()->instance(SupportTrust::class, new class($delegate, $file) implements SupportTrust
    {
        public function __construct(private $delegate, private string $file) {}

        public function current(): SupportTrustState
        {
            expect(DB::transactionLevel())->toBe(0);
            $state = $this->delegate->current();
            file_put_contents($this->file, bin2hex(random_bytes(32)));

            return $state;
        }
    });
    tenantCommand($this, $this->supportPath, $this->supportInput, $this->requester)->assertUnauthorized()->assertJsonPath('error', 'invalid_workload_identity');
    expect(DB::table('app.support_requests')->count())->toBe(0);
});
