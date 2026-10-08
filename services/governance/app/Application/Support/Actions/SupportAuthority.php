<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportTrustState;
use App\Domain\Tenancy\GovernanceLedger;
use App\Domain\Tenancy\PermissionMatrix;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use stdClass;

final class SupportAuthority
{
    public function __construct(private readonly AuthorizeTenant $tenancy) {}

    public function session(string $hash, string $actor, SupportTrustState $trust, bool $recent = false): stdClass
    {
        $session = DB::table('app.federated_sessions as s')
            ->join('app.federated_actors as a', 'a.id', '=', 's.actor_id')
            ->join('app.oidc_connections as c', 'c.revision', '=', 's.connection_revision')
            ->where('s.token_hash', $hash)->where('s.actor_id', $actor)->where('s.audience', 'console')
            ->where('s.connection_revision', $trust->connectionRevision)->whereColumn('a.issuer', 'c.issuer')
            ->whereNull('a.disabled_at')->whereNull('s.revoked_at')->where('s.expires_at', '>', now())->first(['s.*']);
        if ($session === null || ! in_array($session->provider_key_sha256, $trust->keyThumbprints, true)) {
            throw new IdentityDenied('support_authority_changed', 403);
        }
        if ($recent && Carbon::parse($session->created_at)->lte(now()->subMinutes(5))) {
            throw new IdentityDenied('support_reauthentication_required', 403);
        }

        return $session;
    }

    /** @param array<string, mixed> $binding */
    public function membership(string $actor, string $tenant, array $binding, bool $owner = false): stdClass
    {
        $scope = ['site_id' => $binding['site_id'], 'environment' => $binding['environment']];
        $member = $this->tenancy->handle(new FederatedIdentity($actor, false), $tenant, $owner ? 'tenant.manage' : 'tenant.read', $scope);
        if (! PermissionMatrix::within($member->site_id, $member->environment, null, $scope)
            || ($owner && $member->role !== 'tenant_admin')) {
            throw new IdentityDenied('forbidden', 403);
        }

        return $member;
    }

    /** @param array<string, mixed> $binding */
    public function security(string $actor, string $tenant, array $binding, string $role, ?string $id = null): stdClass
    {
        $query = DB::table('app.support_security_grants')->where('actor_id', $actor)->where('tenant_id', $tenant)
            ->where('site_id', $binding['site_id'])->where('environment', $binding['environment'])->where('role', $role)
            ->whereNull('revoked_at')->where('expires_at', '>', now());
        if ($id !== null) {
            $query->where('id', $id);
        }
        $grant = $query->orderBy('id')->first();
        if ($grant === null) {
            throw new IdentityDenied('forbidden', 403);
        }

        return $grant;
    }

    /** @param array<string, mixed> $binding */
    public function visible(FederatedIdentity $actor, stdClass $request, array $binding): void
    {
        if (in_array($actor->subject, [$request->requester_id, $request->executor_id], true)) {
            return;
        }
        try {
            $this->membership($actor->subject, $request->tenant_id, $binding, true);

            return;
        } catch (IdentityDenied) {
            foreach (['approver', 'reviewer'] as $role) {
                try {
                    $this->security($actor->subject, $request->tenant_id, $binding, $role);

                    return;
                } catch (IdentityDenied) {
                    // No installation-wide or former-approver read fallback.
                }
            }
        }
        throw new IdentityDenied('not_found', 404);
    }

    /** @param array<string, mixed> $binding
     * @return list<array<string, mixed>>
     */
    public function resources(string $tenant, array $binding): array
    {
        $result = [];
        foreach ($binding['resources'] as $resource) {
            $table = match ($resource['kind']) {
                'membership' => 'app.tenant_memberships', 'grant' => 'app.delegated_grants',
                default => throw new IdentityDenied('support_binding_invalid', 422),
            };
            $row = DB::table($table)->where('tenant_id', $tenant)->where('id', $resource['id'])
                ->where('site_id', $binding['site_id'])->where('environment', $binding['environment'])->first();
            if ($row === null) {
                throw new IdentityDenied('support_resource_changed', 409);
            }
            $result[] = ['kind' => $resource['kind'], 'id' => $row->id, 'revision' => $row->revision,
                'site_id' => $row->site_id, 'environment' => $row->environment,
                ...($resource['kind'] === 'membership'
                    ? ['role' => $row->role, 'state' => $row->state, 'expires_at' => self::time($row->expires_at)]
                    : ['action' => $row->action, 'membership_revision' => $row->membership_revision,
                        'expires_at' => self::time($row->expires_at), 'revoked_at' => self::time($row->revoked_at)])];
        }

        return $result;
    }

    public static function securityFingerprint(stdClass $grant): string
    {
        return GovernanceLedger::digest(['id' => $grant->id, 'revision' => $grant->revision,
            'actor_id' => $grant->actor_id, 'role' => $grant->role, 'tenant_id' => $grant->tenant_id,
            'site_id' => $grant->site_id, 'environment' => $grant->environment]);
    }

    public static function time(?string $value): ?string
    {
        return $value === null ? null : Carbon::parse($value)->utc()->toIso8601String();
    }
}
