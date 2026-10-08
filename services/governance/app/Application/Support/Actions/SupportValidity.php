<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Application\Identity\Contracts\ServiceCredentials;
use App\Application\Tenancy\Actions\AuthorizeTenant;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportExpiry;
use App\Domain\Support\SupportPolicy;
use App\Domain\Support\SupportTrustState;
use App\Domain\Tenancy\GovernanceLedger;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use stdClass;

final class SupportValidity
{
    public function __construct(private readonly SupportAuthority $authority, private readonly ServiceCredentials $credentials) {}

    /** @return array<string, mixed> */
    public function handle(stdClass $row, SupportTrustState $trust): array
    {
        if (in_array($row->state, SupportPolicy::TERMINAL, true)) {
            throw new IdentityDenied('support_not_effective', 409);
        }
        $binding = json_decode($row->binding_json, true, 32, JSON_THROW_ON_ERROR);
        try {
            if (! hash_equals($row->binding_sha256, GovernanceLedger::digest($binding))
                || $row->policy_version !== SupportPolicy::VERSION || $row->connection_revision !== $trust->connectionRevision
                || ! hash_equals($row->console_fingerprint, $this->credentials->fingerprint('console'))
                || ! hash_equals($row->admission_binding, (string) DB::table('app.identity_admission')->where('id', 1)->value('binding_sha256'))
                || $binding['tenant_revision'] !== DB::table('app.tenants')->where('id', $row->tenant_id)->value('revision')
                || DB::table('app.tenants')->where('id', $row->tenant_id)->value('state') !== 'active') {
                throw new IdentityDenied('support_authority_changed', 403);
            }
            $this->authority->session($row->requester_session_hash, $row->requester_id, $trust);
            $member = $this->authority->membership($row->requester_id, $row->tenant_id, $binding);
            if (! hash_equals($row->requester_authority, AuthorizeTenant::fingerprint($member))) {
                throw new IdentityDenied('support_authority_changed', 403);
            }
            $approvals = DB::table('app.support_approvals')->where('request_id', $row->id)->get();
            $resources = $approvals->isEmpty() ? null : GovernanceLedger::digest(['resources' => $this->authority->resources($row->tenant_id, $binding)]);
            foreach ($approvals as $approval) {
                $this->authority->session($approval->session_hash, $approval->actor_id, $trust);
                $fingerprint = $approval->role === 'tenant'
                    ? AuthorizeTenant::fingerprint($this->authority->membership($approval->actor_id, $row->tenant_id, $binding, true))
                    : SupportAuthority::securityFingerprint($this->authority->security($approval->actor_id, $row->tenant_id, $binding, 'approver', $approval->security_grant_id));
                if (Carbon::parse($approval->expires_at)->lte(now()) || ! hash_equals($approval->authority_sha256, $fingerprint)
                    || ! hash_equals($approval->resources_sha256, (string) $resources)) {
                    throw new IdentityDenied('support_authority_changed', 403);
                }
            }
            if ($row->executor_session_hash !== null) {
                $this->authority->session($row->executor_session_hash, $row->executor_id, $trust);
            }
        } catch (IdentityDenied $error) {
            // Once underlying authority changes, a later regrant/key restoration
            // cannot reactivate this request. A new independently approved request is needed.
            if ($error->status !== 503) {
                SupportExpiry::end($row, 'invalidated', null);
            }
            throw new IdentityDenied($error->status === 503 ? 'support_trust_unavailable' : 'support_authority_changed', $error->status === 503 ? 503 : 403);
        }

        return $binding;
    }
}
