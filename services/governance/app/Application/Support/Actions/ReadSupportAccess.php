<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Application\Identity\Data\FederatedIdentity;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Support\SupportPolicy;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use stdClass;

final class ReadSupportAccess
{
    public function __construct(private readonly SupportTransaction $transaction) {}

    /** @return array<string, mixed> */
    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $workload, string $tenant, string $id, bool $history = false, ?string $before = null): array
    {
        return $this->transaction->handle($token, $workload, false, function (FederatedIdentity $actor) use ($tenant, $id, $history, $before): array {
            $row = $this->transaction->request($actor, $tenant, $id);
            if ($history) {
                $query = DB::table('app.support_audit')->where('tenant_id', $tenant)->where('resource_id', $id);
                if ($before !== null) {
                    $position = (clone $query)->where('id', $before)->first();
                    if ($position === null) {
                        throw new IdentityDenied('not_found', 404);
                    }
                    $query->where(fn ($q) => $q->where('occurred_at', '<', $position->occurred_at)
                        ->orWhere(fn ($q) => $q->where('occurred_at', $position->occurred_at)->where('id', '<', $position->id)));
                }
                $rows = $query->orderByDesc('occurred_at')->orderByDesc('id')->limit(101)->get();
                $more = $rows->count() > 100;
                $page = $rows->take(100)->map(static fn (stdClass $event): array => ['id' => $event->id, 'event' => $event->event,
                    'actor_id' => $event->actor_id, 'revision' => $event->revision, 'occurred_at' => SupportAuthority::time($event->occurred_at),
                    'correlation_id' => $event->correlation_id, 'facts' => json_decode($event->payload_json, true, 32, JSON_THROW_ON_ERROR)['facts']])->values();

                $last = $page->last();

                return ['request_id' => $id, 'events' => $page->all(), 'next_before' => $more && $last !== null ? $last['id'] : null];
            }
            $approvals = DB::table('app.support_approvals')->where('request_id', $id)->orderBy('role')->get(['role', 'actor_id', 'expires_at', 'created_at'])
                ->map(static fn (stdClass $approval): array => ['role' => $approval->role, 'actor_id' => $approval->actor_id,
                    'expires_at' => SupportAuthority::time($approval->expires_at), 'created_at' => SupportAuthority::time($approval->created_at)]);
            $review = DB::table('app.support_reviews')->where('request_id', $id)->first(['actor_id', 'outcome', 'case_reference', 'reviewed_at']);
            if ($review !== null) {
                $review->reviewed_at = SupportAuthority::time($review->reviewed_at);
            }

            return ['id' => $id, 'tenant_id' => $tenant, 'state' => $row->state, 'revision' => $row->revision,
                'binding_sha256' => $row->binding_sha256, 'binding' => json_decode($row->binding_json, true, 32, JSON_THROW_ON_ERROR),
                'approvals' => $approvals->all(), 'effective_until' => SupportAuthority::time($row->effective_until), 'admission_count' => $row->admission_count,
                'review_due_at' => $row->admission_count > 0 ? Carbon::parse($row->effective_until)->addHours(SupportPolicy::REVIEW_HOURS)->toIso8601String() : null,
                'review' => $review, 'authority_use' => 'request_status_only'];
        });
    }
}
