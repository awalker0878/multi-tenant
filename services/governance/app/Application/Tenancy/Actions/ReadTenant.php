<?php

declare(strict_types=1);

namespace App\Application\Tenancy\Actions;

use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Facades\DB;

final class ReadTenant
{
    public function __construct(private readonly AuthorizeTenant $authority) {}

    /** @return array<string, mixed> */
    public function handle(#[\SensitiveParameter] string $token, ?string $tenant, string $view): array
    {
        return DB::transaction(function () use ($token, $tenant, $view): array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->authority->actor($token);
            if ($tenant === null) {
                $tenants = DB::table('app.tenants as t')->join('app.tenant_memberships as m', 'm.tenant_id', '=', 't.id')
                    ->where('m.actor_id', $actor->subject)->where('m.state', 'active')
                    ->where(fn ($q) => $q->whereNull('m.expires_at')->orWhere('m.expires_at', '>', now()))
                    ->orderBy('t.name')->limit(200)->get(['t.id', 't.name', 't.state', 't.revision', 'm.role', 'm.site_id', 'm.environment']);

                return ['tenants' => $tenants->all(), 'installation_administrator' => $actor->installationAdministrator];
            }
            $permission = match ($view) {
                'tenant' => 'tenant.read', 'memberships' => 'membership.manage', 'grants' => 'grant.manage', 'quota' => 'quota.read', 'audit' => 'audit.read',
                default => throw new IdentityDenied('not_found', 404),
            };
            $member = $this->authority->handle($actor, $tenant, $permission);

            return match ($view) {
                'tenant' => ['tenant' => DB::table('app.tenants')->where('id', $tenant)->first(['id', 'name', 'state', 'revision']),
                    'membership' => ['id' => $member->id, 'role' => $member->role, 'revision' => $member->revision, 'site_id' => $member->site_id, 'environment' => $member->environment]],
                'memberships' => ['memberships' => DB::table('app.tenant_memberships as m')->join('app.federated_actors as a', 'a.id', '=', 'm.actor_id')->where('m.tenant_id', $tenant)->orderBy('m.id')->limit(200)->get(['m.*', 'a.subject'])->all()],
                'grants' => ['grants' => DB::table('app.delegated_grants')->where('tenant_id', $tenant)->orderBy('id')->limit(200)->get()->all()],
                'quota' => $this->quota($tenant),
                'audit' => ['audit' => DB::table('app.governance_audit')->where('tenant_id', $tenant)->orderByDesc('occurred_at')->orderBy('id')->limit(100)->get()->map(function (\stdClass $entry): \stdClass {
                    // Preserve the published v1 UUID wire type. Nil is a system
                    // sentinel, never an authenticatable federated identity.
                    $entry->actor_id ??= '00000000-0000-0000-0000-000000000000';

                    return $entry;
                })->all()],
            };
        });
    }

    /** @return array<string, mixed> */
    private function quota(string $tenant): array
    {
        $quota = DB::table('app.tenant_quotas')->where('tenant_id', $tenant)->first();

        return ['revision' => $quota->revision ?? 0, 'entitlement' => $quota === null ? null : json_decode($quota->limits_json, true, 16, JSON_THROW_ON_ERROR),
            'observed_capacity' => null, 'reservations' => null];
    }
}
