<?php

declare(strict_types=1);

namespace App\Application\Tenancy\Actions;

use App\Application\Identity\Actions\ResolveIdentitySession;
use App\Application\Identity\Data\FederatedIdentity;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Tenancy\GovernanceLedger;
use App\Domain\Tenancy\PermissionMatrix;
use Illuminate\Support\Facades\DB;

final class AuthorizeTenant
{
    public function __construct(private readonly ResolveIdentitySession $identity) {}

    public function actor(#[\SensitiveParameter] string $token): FederatedIdentity
    {
        $actor = $this->identity->handle($token);
        if (! $actor instanceof FederatedIdentity) {
            throw new IdentityDenied('forbidden', 403);
        }

        return $actor;
    }

    /** @param array{site_id?: string|null, environment?: string|null, resource_id?: string|null} $scope */
    public function handle(FederatedIdentity $actor, string $tenant, string $action, array $scope = []): \stdClass
    {
        $membership = DB::table('app.tenant_memberships as membership')
            ->join('app.federated_actors as actors', 'actors.id', '=', 'membership.actor_id')->whereNull('actors.disabled_at')
            ->join('app.tenants as tenants', 'tenants.id', '=', 'membership.tenant_id')
            ->where('membership.tenant_id', $tenant)->where('membership.actor_id', $actor->subject)
            ->where('membership.state', 'active')
            ->where(fn ($q) => $q->whereNull('membership.expires_at')->orWhere('membership.expires_at', '>', now()))
            ->first(['membership.*', 'tenants.state as tenant_state']);
        // Identical response for an unknown tenant and a tenant without current membership.
        if ($membership === null || ($membership->tenant_state !== 'active' && $action !== 'tenant.manage')) {
            throw new IdentityDenied('not_found', 404);
        }
        $membership->decision_grant_id = null;
        $membership->decision_grant_revision = null;
        if ($action === 'tenant.read') {
            return $membership;
        }
        if (! PermissionMatrix::within($membership->site_id, $membership->environment, null, $scope)) {
            throw new IdentityDenied('forbidden', 403);
        }
        if (in_array($action, PermissionMatrix::ROLES[$membership->role] ?? [], true)) {
            return $membership;
        }
        $grants = DB::table('app.delegated_grants')->where('tenant_id', $tenant)
            ->where('membership_id', $membership->id)->where('membership_revision', $membership->revision)
            ->where('action', $action)->whereNull('revoked_at')->where('expires_at', '>', now())->orderBy('id')->get();
        foreach ($grants as $grant) {
            if (PermissionMatrix::within($grant->site_id, $grant->environment, $grant->resource_id, $scope)) {
                $membership->decision_grant_id = $grant->id;
                $membership->decision_grant_revision = $grant->revision;

                return $membership;
            }
        }
        throw new IdentityDenied('forbidden', 403);
    }

    public static function fingerprint(\stdClass $membership): string
    {
        return GovernanceLedger::digest(['membership_id' => $membership->id, 'revision' => $membership->revision,
            'role' => $membership->role, 'grant_id' => $membership->decision_grant_id, 'grant_revision' => $membership->decision_grant_revision]);
    }
}
