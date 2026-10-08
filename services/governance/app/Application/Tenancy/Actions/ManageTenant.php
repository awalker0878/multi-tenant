<?php

declare(strict_types=1);

namespace App\Application\Tenancy\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\GovernanceLedger;
use App\Domain\Tenancy\PermissionMatrix;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class ManageTenant
{
    public function __construct(private readonly ExecuteGovernanceCommand $commands) {}

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, ?string $tenant, string $operation, string $key, array $input): array
    {
        $permission = match ($operation) {
            'create' => 'tenants.create', 'state' => 'tenant.manage',
            'membership' => 'membership.manage', 'grant', 'revoke_grant' => 'grant.manage', 'quota' => 'quota.manage',
            default => throw new IdentityDenied('forbidden', 403),
        };

        return $this->commands->handle($token, $tenant, $permission, $operation, $key, $input,
            function (FederatedIdentity $actor) use ($tenant, $operation, $input): array {
                if ($operation === 'create') {
                    return $this->create($actor, $input);
                }
                if ($tenant === null) {
                    throw new IdentityDenied('not_found', 404);
                }

                return match ($operation) {
                    'state' => $this->state($actor, $tenant, $input),
                    'membership' => $this->membership($actor, $tenant, $input),
                    'grant' => $this->grant($actor, $tenant, $input),
                    'revoke_grant' => $this->revokeGrant($actor, $tenant, $input),
                    'quota' => $this->quota($actor, $tenant, $input),
                };
            });
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    private function create(FederatedIdentity $actor, array $input): array
    {
        $id = (string) Str::uuid();
        DB::table('app.tenants')->insert(['id' => $id, 'name' => $input['name'], 'state' => 'active', 'revision' => 1, 'created_by' => $actor->subject, 'created_at' => now()]);
        // An installation administrator has no automatic membership in the new tenant.
        $administrator = $this->subject($input['administrator_subject']);
        DB::table('app.tenant_memberships')->insert(['id' => (string) Str::uuid(), 'tenant_id' => $id, 'actor_id' => $administrator,
            'role' => 'tenant_admin', 'state' => 'active', 'revision' => 1]);
        $result = ['id' => $id, 'name' => $input['name'], 'state' => 'active', 'revision' => 1, 'administrator_id' => $administrator];
        GovernanceLedger::record($id, $actor->subject, 'governance.tenant.changed', $id, 1, $result);

        return $result;
    }

    private function subject(string $subject): string
    {
        $connection = DB::table('app.oidc_installation as i')->join('app.oidc_connections as c', 'c.revision', '=', 'i.active_revision')->where('i.id', 1)->first(['c.issuer']);
        if ($connection === null) {
            throw new IdentityDenied('identity_unavailable', 503);
        }
        $actor = DB::table('app.federated_actors')->where('issuer', $connection->issuer)->where('subject', $subject)->first();
        if ($actor !== null) {
            if ($actor->disabled_at !== null) {
                throw new IdentityDenied('invalid_subject', 422);
            }

            return $actor->id;
        }
        $id = (string) Str::uuid();
        DB::table('app.federated_actors')->insert(['id' => $id, 'issuer' => $connection->issuer, 'subject' => $subject]);

        return $id;
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    private function state(FederatedIdentity $actor, string $tenant, array $input): array
    {
        $current = DB::table('app.tenants')->where('id', $tenant)->first();
        if ($current === null || $current->revision !== $input['revision']) {
            throw new IdentityDenied('revision_conflict', 409);
        }
        $result = ['id' => $tenant, 'state' => $input['state'], 'revision' => $current->revision + 1];
        DB::table('app.tenants')->where('id', $tenant)->update(['state' => $result['state'], 'revision' => $result['revision']]);
        GovernanceLedger::record($tenant, $actor->subject, 'governance.tenant.changed', $tenant, $result['revision'], $result);

        return $result;
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    private function membership(FederatedIdentity $actor, string $tenant, array $input): array
    {
        $subject = $this->subject($input['subject']);
        $query = DB::table('app.tenant_memberships')->where('tenant_id', $tenant)->where('actor_id', $subject);
        $current = $query->first();
        if (($current->revision ?? 0) !== $input['revision']) {
            throw new IdentityDenied('revision_conflict', 409);
        }
        if ($current !== null && $current->role === 'tenant_admin' && $current->state === 'active'
            && ($input['role'] !== 'tenant_admin' || $input['state'] !== 'active' || $input['site_id'] !== null || $input['environment'] !== null || $input['expires_at'] !== null)
            && ! DB::table('app.tenant_memberships')->where('tenant_id', $tenant)->where('id', '!=', $current->id)
                ->where('role', 'tenant_admin')->where('state', 'active')->whereNull('site_id')->whereNull('environment')
                ->where(fn ($q) => $q->whereNull('expires_at')->orWhere('expires_at', '>', now()))->exists()) {
            throw new IdentityDenied('last_tenant_administrator', 409);
        }
        $id = $current->id ?? (string) Str::uuid();
        $values = ['role' => $input['role'], 'state' => $input['state'], 'site_id' => $input['site_id'],
            'environment' => $input['environment'], 'expires_at' => $input['expires_at'] === null ? null : Carbon::parse($input['expires_at']),
            'revision' => $input['revision'] + 1];
        if ($current === null) {
            $query->insert(['id' => $id, 'tenant_id' => $tenant, 'actor_id' => $subject] + $values);
        } else {
            $query->update($values);
        }
        $result = ['id' => $id, 'actor_id' => $subject] + $values;
        GovernanceLedger::record($tenant, $actor->subject, 'governance.membership.changed', $id, $values['revision'], $result);

        return $result;
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    private function grant(FederatedIdentity $actor, string $tenant, array $input): array
    {
        $member = DB::table('app.tenant_memberships')->where('tenant_id', $tenant)->where('id', $input['membership_id'])->where('state', 'active')
            ->where(fn ($q) => $q->whereNull('expires_at')->orWhere('expires_at', '>', now()))->first();
        if ($member === null || ! PermissionMatrix::within($member->site_id, $member->environment, null, $input)) {
            throw new IdentityDenied('invalid_grant_scope', 422);
        }
        $id = (string) Str::uuid();
        $values = ['id' => $id, 'tenant_id' => $tenant, 'membership_id' => $member->id, 'membership_revision' => $member->revision,
            'action' => $input['action'], 'site_id' => $input['site_id'], 'environment' => $input['environment'], 'resource_id' => $input['resource_id'],
            'expires_at' => Carbon::parse($input['expires_at']), 'revision' => 1, 'created_by' => $actor->subject];
        DB::table('app.delegated_grants')->insert($values);
        GovernanceLedger::record($tenant, $actor->subject, 'governance.grant.changed', $id, 1, $values);

        return $values;
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    private function revokeGrant(FederatedIdentity $actor, string $tenant, array $input): array
    {
        $query = DB::table('app.delegated_grants')->where('tenant_id', $tenant)->where('id', $input['grant_id']);
        $grant = $query->first();
        if ($grant === null) {
            throw new IdentityDenied('not_found', 404);
        }
        if ($grant->revision !== $input['revision'] || $grant->revoked_at !== null) {
            throw new IdentityDenied('revision_conflict', 409);
        }
        $result = ['id' => $grant->id, 'revision' => $grant->revision + 1, 'revoked_at' => now()->toIso8601String(), 'reason' => $input['reason']];
        $query->update(['revision' => $result['revision'], 'revoked_at' => now()]);
        GovernanceLedger::record($tenant, $actor->subject, 'governance.grant.revoked', $grant->id, $result['revision'], $result);

        return $result;
    }

    /** @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    private function quota(FederatedIdentity $actor, string $tenant, array $input): array
    {
        $query = DB::table('app.tenant_quotas')->where('tenant_id', $tenant);
        $current = $query->first();
        if (($current->revision ?? 0) !== $input['revision']) {
            throw new IdentityDenied('revision_conflict', 409);
        }
        $revision = $input['revision'] + 1;
        $values = ['revision' => $revision, 'limits_json' => json_encode($input['entitlement'], JSON_THROW_ON_ERROR)];
        if ($current === null) {
            $query->insert(['tenant_id' => $tenant] + $values);
        } else {
            $query->update($values);
        }
        $result = ['tenant_id' => $tenant, 'revision' => $revision, 'entitlement' => $input['entitlement']];
        GovernanceLedger::record($tenant, $actor->subject, 'governance.quota.changed', $tenant, $revision, $result);

        return $result;
    }
}
