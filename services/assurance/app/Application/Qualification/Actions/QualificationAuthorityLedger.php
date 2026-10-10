<?php

declare(strict_types=1);

namespace App\Application\Qualification\Actions;

use App\Domain\Qualification\NativeQualification;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Assurance-owned, per-scope serialized publication and immutable decision history.
 *
 * Publication is not a substitute for verifying the signed bundle. The caller must
 * have independently verified new publish/restore decisions before invoking mutate.
 */
final class QualificationAuthorityLedger
{
    /** @param array<string, mixed> $scope
     * @return array<string, mixed>|null */
    public function current(array $scope): ?array
    {
        $row = DB::table('app.qualification_authority_heads')
            ->where('scope_sha256', NativeQualification::digest($scope))->first();

        return $row === null ? null : $this->projection($row);
    }

    /** @param array<string, mixed> $scope
     * @param array<string, mixed>|null $bundle
     * @return array<string, mixed> */
    public function mutate(
        array $scope,
        string $operation,
        string $commandId,
        int $expectedEpoch,
        string $reason,
        ?array $bundle,
        string $decisionSha,
        int $decisionRevision,
        string $reviewerId
    ): array {
        abort_unless(in_array($operation, ['publish', 'restore', 'suspend', 'revoke'], true)
            && $expectedEpoch >= 0 && $reason !== '' && strlen($reason) <= 1024
            && $reviewerId !== '' && strlen($reviewerId) <= 256, 422);
        $scopeSha = NativeQualification::digest($scope);
        $requestSha = NativeQualification::digest([
            'scope' => $scope, 'operation' => $operation, 'expected_epoch' => $expectedEpoch,
            'reason' => $reason, 'bundle' => $bundle, 'decision_sha256' => $decisionSha,
            'decision_revision' => $decisionRevision, 'reviewer_id' => $reviewerId,
        ]);

        return DB::transaction(function () use (
            $scope, $scopeSha, $operation, $commandId, $expectedEpoch, $reason,
            $bundle, $decisionSha, $decisionRevision, $reviewerId, $requestSha
        ): array {
            // Collision only introduces unnecessary serialization, never mixed authority.
            DB::select('SELECT pg_advisory_xact_lock(hashtext(?))', [$scopeSha]);
            $existing = DB::table('app.qualification_authority_events')
                ->where('scope_sha256', $scopeSha)->where('command_id', $commandId)->first();
            if ($existing !== null) {
                abort_unless(hash_equals($existing->request_sha256, $requestSha), 409, 'publication_command_conflict');

                return json_decode($existing->result, true, 64, JSON_THROW_ON_ERROR);
            }
            $head = DB::table('app.qualification_authority_heads')
                ->where('scope_sha256', $scopeSha)->lockForUpdate()->first();
            $epoch = $head === null ? 0 : (int) $head->authority_epoch;
            abort_unless($expectedEpoch === $epoch, 409, 'qualification_epoch_changed');

            if ($operation === 'suspend' && $head !== null && $head->state === 'suspended') {
                // A repeat failed observation must not clear or advance suspension.
                return $this->projection($head);
            }
            if ($operation === 'publish' || $operation === 'restore') {
                abort_unless($bundle !== null && preg_match('/^[a-f0-9]{64}$/', $decisionSha) === 1
                    && $decisionRevision > 0, 422, 'verified_publication_required');
                abort_if($operation === 'publish' && $head !== null && $head->state !== 'qualified', 409,
                    'restore_requires_new_review');
                abort_unless($operation !== 'restore' || ($head !== null
                    && in_array($head->state, ['suspended', 'revoked'], true)), 409,
                    'restoration_requires_prior_hold');
                if ($head !== null) {
                    abort_unless($decisionRevision > (int) $head->decision_revision
                        && $decisionSha !== $head->decision_sha256
                        && $reviewerId !== $head->reviewer_id, 409, 'independent_new_review_required');
                }
                $state = 'qualified';
                $stored = $bundle;
                $newDecision = $decisionSha;
                $newRevision = $decisionRevision;
            } else {
                abort_unless($head !== null && in_array($head->state, ['qualified', 'suspended'], true), 409,
                    'qualification_not_active');
                $state = $operation === 'revoke' ? 'revoked' : 'suspended';
                $stored = json_decode($head->bundle, true, 64, JSON_THROW_ON_ERROR);
                $newDecision = $head->decision_sha256;
                $newRevision = (int) $head->decision_revision;
                // Preserve the previous independently signed reviewer for restore comparison.
                $reviewerId = $head->reviewer_id;
            }

            $nextEpoch = $epoch + 1;
            $now = time();
            $projection = [
                'state' => $state, 'authority_epoch' => $nextEpoch,
                'decision_sha256' => $newDecision, 'decision_revision' => $newRevision,
                'reviewer_id' => $reviewerId, 'bundle' => $stored,
            ];
            $previousEvent = $head === null ? null : $head->last_event_sha256;
            $eventSha = NativeQualification::digest([
                'previous_event_sha256' => $previousEvent,
                'scope_sha256' => $scopeSha, 'authority_epoch' => $nextEpoch,
                'operation' => $operation, 'request_sha256' => $requestSha,
                'result' => $projection, 'recorded_at' => $now,
            ]);
            $values = [
                'tenant' => $scope['tenant_id'],
                'authority_epoch' => $nextEpoch, 'state' => $state,
                'decision_sha256' => $newDecision, 'decision_revision' => $newRevision,
                'reviewer_id' => $reviewerId,
                'bundle' => json_encode($stored, JSON_THROW_ON_ERROR),
                'last_event_sha256' => $eventSha, 'updated_at' => $now,
            ];
            if ($head === null) {
                DB::table('app.qualification_authority_heads')->insert(
                    ['scope_sha256' => $scopeSha] + $values
                );
            } else {
                DB::table('app.qualification_authority_heads')
                    ->where('scope_sha256', $scopeSha)->update($values);
            }
            $eventId = (string) Str::uuid();
            DB::table('app.qualification_authority_events')->insert([
                'event_id' => $eventId, 'command_id' => $commandId,
                'scope_sha256' => $scopeSha, 'tenant' => $scope['tenant_id'],
                'authority_epoch' => $nextEpoch, 'operation' => $operation,
                'request_sha256' => $requestSha,
                'previous_event_sha256' => $previousEvent, 'event_sha256' => $eventSha,
                'result' => json_encode($projection, JSON_THROW_ON_ERROR),
                'recorded_at' => $now,
            ]);
            DB::table('app.qualification_authority_outbox')->insert([
                'event_id' => $eventId, 'scope_sha256' => $scopeSha,
                'authority_epoch' => $nextEpoch,
                'payload' => json_encode([
                    'event_id' => $eventId, 'tenant_id' => $scope['tenant_id'],
                    'scope_sha256' => $scopeSha,
                    'authority_epoch' => $nextEpoch, 'operation' => $operation,
                    'decision_sha256' => $newDecision, 'state' => $state,
                    'event_sha256' => $eventSha,
                ], JSON_THROW_ON_ERROR),
                'created_at' => $now,
            ]);

            return $projection;
        }, 3);
    }

    /** @return array<string, mixed> */
    private function projection(object $row): array
    {
        return [
            'state' => $row->state,
            'authority_epoch' => (int) $row->authority_epoch,
            'decision_sha256' => $row->decision_sha256,
            'decision_revision' => (int) $row->decision_revision,
            'reviewer_id' => $row->reviewer_id,
            'bundle' => json_decode($row->bundle, true, 64, JSON_THROW_ON_ERROR),
        ];
    }
}
