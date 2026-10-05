<?php

declare(strict_types=1);

use App\Application\Approvals\Actions\ExpireApprovals;
use App\Application\Approvals\Contracts\ImmutablePlanSource;
use App\Domain\Tenancy\GovernanceLedger;
use App\Infrastructure\Approvals\PlanningPlanSource;
use App\Infrastructure\Messaging\GovernanceEventEncoder;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Tests\Support\SyntheticPlanSource;

beforeEach(function (): void {
    initializeFederationFixture($this);
    $this->tenant = tenantCommand($this, '/v1/tenants', ['name' => 'Approval tenant', 'administrator_subject' => 'immutable-admin-subject'])->assertCreated()->json('id');
    $this->authorMember = tenantMember($this, $this->tenant, 'author', 'author');
    $this->reviewerMember = tenantMember($this, $this->tenant, 'reviewer', 'reviewer');
    $this->operatorMember = tenantMember($this, $this->tenant, 'operator', 'operator');
    $this->author = federatedLogin($this, 'author');
    $this->reviewer = federatedLogin($this, 'reviewer');
    $this->operator = federatedLogin($this, 'operator');
    $binding = ['plan_id' => '550e8400-e29b-41d4-a716-446655440001', 'revision' => 1, 'tenant_id' => $this->tenant,
        'action' => 'application.migrate', 'site_id' => 'site-a', 'environment' => 'development', 'resource_id' => 'app-a',
        'requested_by' => $this->authorMember['actor_id'], 'executor_ids' => [$this->operatorMember['actor_id']], 'valid_until' => time() + 7200];
    $this->plan = $binding + ['digest' => GovernanceLedger::digest($binding)];
    $this->source = new SyntheticPlanSource($this->plan);
    app()->instance(ImmutablePlanSource::class, $this->source);
    $this->input = ['plan_id' => $this->plan['plan_id'], 'plan_revision' => 1, 'plan_digest' => $this->plan['digest'], 'expires_at' => now()->addHour()->toIso8601String()];
    $this->path = '/v1/tenants/'.$this->tenant.'/approvals';
    $this->use = ['plan_id' => $this->plan['plan_id'], 'plan_revision' => 1, 'plan_digest' => $this->plan['digest'],
        'action' => 'application.migrate', 'scope' => ['site_id' => 'site-a', 'environment' => 'development', 'resource_id' => 'app-a']];
});

afterEach(function (): void {
    unlink($this->credentialFile);
    $this->travelBack();
});

function requestApproval(object $test): string
{
    return tenantCommand($test, $test->path, $test->input, $test->author)->assertCreated()->json('id');
}
function approvePlan(object $test): string
{
    $id = requestApproval($test);
    tenantCommand($test, $test->path.'/'.$id.'/approve', ['revision' => 1, 'reason' => 'Independent synthetic review'], $test->reviewer)->assertOk()->assertJsonPath('state', 'approved');

    return $id;
}

it('binds an independent approval to an immutable plan and named executor', function (): void {
    $id = approvePlan($this);
    $this->withHeader('X-Console-Session', $this->operator)->postJson($this->path.'/'.$id.'/validations', $this->use)->assertOk()->assertJsonPath('authority_use', 'observation_only');
    $this->getJson($this->path.'/'.$id)->assertOk()->assertJsonPath('binding.digest', $this->plan['digest'])->assertJsonPath('revision', 2);
    expect(DB::table('app.governance_audit')->where('resource_id', $id)->pluck('event')->all())->toBe(['governance.approval.requested', 'governance.approval.approved']);
});

it('denies self-approval even if the requestor also has a reviewer grant', function (): void {
    tenantCommand($this, '/v1/tenants/'.$this->tenant.'/grants', ['membership_id' => $this->authorMember['id'], 'action' => 'approval.decide',
        'site_id' => null, 'environment' => null, 'resource_id' => null, 'expires_at' => now()->addHour()->toIso8601String()])->assertOk();
    $id = requestApproval($this);
    tenantCommand($this, $this->path.'/'.$id.'/approve', ['revision' => 1, 'reason' => 'Self-review denied'], $this->author)->assertForbidden()->assertJsonPath('error', 'independent_approver_required');
    expect(DB::table('app.approvals')->where('id', $id)->value('state'))->toBe('requested');
});

it('denies a named executor from approving even if given approval authority', function (): void {
    tenantCommand($this, '/v1/tenants/'.$this->tenant.'/grants', ['membership_id' => $this->operatorMember['id'], 'action' => 'approval.decide',
        'site_id' => null, 'environment' => null, 'resource_id' => null, 'expires_at' => now()->addHour()->toIso8601String()])->assertOk();
    $id = requestApproval($this);
    tenantCommand($this, $this->path.'/'.$id.'/approve', ['revision' => 1, 'reason' => 'Executor-review denied'], $this->operator)->assertForbidden();
});

it('rejects every changed approval binding rather than widening the approved scope', function (string $field, mixed $value): void {
    $id = approvePlan($this);
    $input = $this->use;
    if (str_starts_with($field, 'scope.')) {
        $input['scope'][substr($field, 6)] = $value;
    } else {
        $input[$field] = $value;
    }
    $this->withHeader('X-Console-Session', $this->operator)->postJson($this->path.'/'.$id.'/validations', $input)->assertForbidden();
})->with([
    ['plan_id', '550e8400-e29b-41d4-a716-446655440002'], ['plan_revision', 2], ['plan_digest', str_repeat('a', 64)],
    ['action', 'application.retire'], ['scope.site_id', 'site-b'], ['scope.environment', 'production'], ['scope.resource_id', 'app-b'],
]);

it('denies an unnamed executor and cross-tenant approval identifiers', function (): void {
    $id = approvePlan($this);
    tenantMember($this, $this->tenant, 'other-operator', 'operator');
    $other = federatedLogin($this, 'other-operator');
    $this->withHeader('X-Console-Session', $other)->postJson($this->path.'/'.$id.'/validations', $this->use)->assertForbidden();
    $this->getJson('/v1/tenants/550e8400-e29b-41d4-a716-446655440003/approvals/'.$id)->assertNotFound();
});

it('records rejection and revocation without destroying history or permitting decision reuse', function (): void {
    $rejected = requestApproval($this);
    tenantCommand($this, $this->path.'/'.$rejected.'/reject', ['revision' => 1, 'reason' => 'Not ready'], $this->reviewer)->assertOk()->assertJsonPath('state', 'rejected');
    tenantCommand($this, $this->path.'/'.$rejected.'/approve', ['revision' => 2, 'reason' => 'Cannot reopen'], $this->reviewer)->assertStatus(409);
    $approved = approvePlan($this);
    tenantCommand($this, $this->path.'/'.$approved.'/revoke', ['revision' => 2, 'reason' => 'Change withdrawn'], $this->reviewer)->assertOk()->assertJsonPath('state', 'revoked');
    $this->withHeader('X-Console-Session', $this->operator)->postJson($this->path.'/'.$approved.'/validations', $this->use)->assertStatus(409);
    expect(DB::table('app.governance_audit')->where('resource_id', $approved)->count())->toBe(3);
});

it('expires approval authoritatively and records the transition once', function (): void {
    $this->input['expires_at'] = now()->addMinute()->toIso8601String();
    $id = approvePlan($this);
    $this->travel(2)->minutes();
    $this->withHeader('X-Console-Session', $this->operator)->postJson($this->path.'/'.$id.'/validations', $this->use)->assertStatus(409);
    $this->getJson($this->path.'/'.$id)->assertOk()->assertJsonPath('state', 'expired');
    expect(DB::table('app.governance_audit')->where('event', 'governance.approval.expired')->count())->toBe(1);
});

it('requires fresh authority and cannot resurrect an approval after membership regrant', function (): void {
    $id = approvePlan($this);
    tenantMember($this, $this->tenant, 'reviewer', 'reviewer', [], 1, 'revoked');
    $this->withHeader('X-Console-Session', $this->operator)->postJson($this->path.'/'.$id.'/validations', $this->use)->assertNotFound();
    tenantMember($this, $this->tenant, 'reviewer', 'reviewer', [], 2, 'active');
    $this->withHeader('X-Console-Session', $this->operator)->postJson($this->path.'/'.$id.'/validations', $this->use)->assertForbidden()->assertJsonPath('error', 'approval_authority_changed');
});

it('fails closed on missing plan authority and detects changed authoritative content', function (): void {
    $this->source->unavailable = true;
    tenantCommand($this, $this->path, $this->input, $this->author)->assertStatus(503);
    $this->source->unavailable = false;
    $id = requestApproval($this);
    $this->source->plan['resource_id'] = 'app-b';
    tenantCommand($this, $this->path.'/'.$id.'/approve', ['revision' => 1, 'reason' => 'Changed plan'], $this->reviewer)->assertStatus(409);
    expect(DB::table('app.approvals')->where('id', $id)->value('state'))->toBe('requested');
});

it('returns the original idempotent decision but rejects changed reason or stale revision', function (): void {
    $id = requestApproval($this);
    $path = $this->path.'/'.$id.'/approve';
    $input = ['revision' => 1, 'reason' => 'Reviewed'];
    $first = tenantCommand($this, $path, $input, $this->reviewer, 'approval-command-01')->assertOk()->json();
    tenantCommand($this, $path, $input, $this->reviewer, 'approval-command-01')->assertOk()->assertExactJson($first);
    tenantCommand($this, $path, ['revision' => 1, 'reason' => 'different'], $this->reviewer, 'approval-command-01')->assertStatus(409);
    tenantCommand($this, $path, $input, $this->reviewer)->assertStatus(409);
});

it('does not fall back to a synthetic plan source in the deployed adapter', function (): void {
    app()->forgetInstance(ImmutablePlanSource::class);
    app()->bind(ImmutablePlanSource::class, PlanningPlanSource::class);
    tenantCommand($this, $this->path, $this->input, $this->author)->assertStatus(503);
    expect(DB::table('app.approvals')->count())->toBe(0);
});

it('records background expiry once without a live session or available plan provider', function (): void {
    $this->input['expires_at'] = now()->addMinute()->toIso8601String();
    $id = approvePlan($this);
    DB::table('app.federated_sessions')->update(['revoked_at' => now()]);
    $this->source->unavailable = true;
    $this->travel(2)->minutes();
    $this->artisan('governance:expire-approvals --limit=1')->expectsOutput('{"expired":1}')->assertSuccessful();
    expect(app(ExpireApprovals::class)->handle())->toBe(0);
    $row = DB::table('app.governance_audit')->where('event', 'governance.approval.expired')->sole();
    expect($row->actor_id)->toBeNull()->and($row->resource_id)->toBe($id)->and($row->revision)->toBe(3);
    $wire = app(GovernanceEventEncoder::class)->encode(DB::table('app.governance_outbox')->where('id', $row->id)->sole());
    expect(json_decode($wire, true)['actor_kind'])->toBe('system');
});

it('preserves the v1 audit UUID contract without attributing system expiry to a user', function (): void {
    $this->input['expires_at'] = now()->addMinute()->toIso8601String();
    approvePlan($this);
    $this->travel(2)->minutes();
    app(ExpireApprovals::class)->handle();
    $audit = $this->withHeader('X-Console-Session', $this->token)->getJson('/v1/tenants/'.$this->tenant.'/audit')->assertOk()->json('audit');
    $expired = array_values(array_filter($audit, fn (array $row): bool => $row['event'] === 'governance.approval.expired'))[0];
    expect($expired['actor_id'])->toBe('00000000-0000-0000-0000-000000000000')
        ->and(json_decode($expired['payload_json'], true)['actor_id'])->toBeNull()
        ->and(DB::table('app.federated_actors')->where('id', $expired['actor_id'])->exists())->toBeFalse();
});

it('expires bounded batches at the exact deadline and leaves terminal decisions intact', function (): void {
    $deadline = now()->addMinute()->startOfSecond();
    $this->input['expires_at'] = $deadline->toIso8601String();
    requestApproval($this);
    approvePlan($this);
    $id = requestApproval($this);
    tenantCommand($this, $this->path.'/'.$id.'/reject', ['revision' => 1, 'reason' => 'Terminal'], $this->reviewer)->assertOk();
    $this->travelTo($deadline);
    $expiry = app(ExpireApprovals::class);
    expect($expiry->handle(1))->toBe(1)->and($expiry->handle(1))->toBe(1)->and($expiry->handle(1))->toBe(0)
        ->and(DB::table('app.approvals')->where('id', $id)->value('state'))->toBe('rejected');
});

it('rolls expiry back if its durable outbox cannot be written', function (): void {
    $this->input['expires_at'] = now()->addMinute()->toIso8601String();
    $id = approvePlan($this);
    $this->travel(2)->minutes();
    DB::statement('DROP TABLE app.governance_outbox');
    expect(fn () => app(ExpireApprovals::class)->handle())->toThrow(QueryException::class)
        ->and(DB::table('app.approvals')->where('id', $id)->value('state'))->toBe('approved')
        ->and(DB::table('app.governance_audit')->where('event', 'governance.approval.expired')->count())->toBe(0);
});
