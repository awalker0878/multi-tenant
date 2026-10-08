<?php

declare(strict_types=1);

namespace App\Application\Evidence\Actions;

use App\Application\Evidence\Contracts\EvidenceAuthority;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class ManageEvidence
{
    public function __construct(private readonly EvidenceAuthority $authority) {}

    /** @param array<string, mixed> $input
     * @return array<string, mixed> */
    public function upload(string $tenant, array $input): array
    {
        $raw = base64_decode($input['content_base64'], true);
        abort_unless(is_string($raw) && strlen($raw) <= 65536 && hash_equals($input['digest'], hash('sha256', $raw)), 422, 'digest_mismatch');
        $observations = json_decode($raw, true, 32, JSON_THROW_ON_ERROR);
        abort_unless(is_array($observations) && array_is_list($observations) && count($observations) >= 1 && count($observations) <= 32, 422);
        $keys = ['tenant_id', 'job_id', 'operation_id', 'attempt_id', 'plan_digest', 'epoch', 'simulation', 'sealed', 'effect_count', 'observed_at', 'outcome'];
        $ids = [];
        foreach ($observations as $observation) {
            // The allowlist is also the redaction policy: arbitrary logs/secrets never enter custody.
            abort_unless(is_array($observation) && count($observation) === count($keys) && array_diff($keys, array_keys($observation)) === []
                && $observation['tenant_id'] === $tenant && $observation['job_id'] === $input['job_id']
                && $observation['plan_digest'] === $input['plan_digest'] && $observation['simulation'] === true
                && $observation['sealed'] === true && $observation['effect_count'] === 1
                && $observation['outcome'] === 'confirmed_succeeded' && is_int($observation['observed_at'])
                && $observation['observed_at'] <= time(), 422, 'invalid_observation');
            foreach (['tenant_id', 'job_id', 'operation_id', 'attempt_id', 'epoch'] as $key) {
                abort_unless(is_string($observation[$key]) && Str::isUuid($observation[$key]), 422);
            }
            abort_if(in_array($observation['operation_id'], $ids, true), 422);
            $ids[] = $observation['operation_id'];
        }
        $metadata = ['tenant_id' => $tenant, 'job_id' => $input['job_id'], 'plan_digest' => $input['plan_digest'],
            'source_revision' => $input['source_revision'], 'digest' => $input['digest'], 'evidence_level' => 'E2'];
        $fingerprint = hash('sha256', json_encode($metadata, JSON_THROW_ON_ERROR));

        return DB::transaction(function () use ($tenant, $input, $raw, $metadata, $fingerprint): array {
            DB::select('SELECT pg_advisory_xact_lock(7604001)');
            $existing = DB::table('app.evidence_uploads')->where('tenant', $tenant)->where('job', $input['job_id'])->where('digest', $input['digest'])->first();
            if ($existing !== null) {
                abort_unless(hash_equals($existing->fingerprint, $fingerprint) && hash_equals($existing->content, $raw), 409);

                return ['id' => $existing->id, 'state' => 'uploaded'];
            }
            $id = (string) Str::uuid();
            DB::table('app.evidence_uploads')->insert(['id' => $id, 'tenant' => $tenant, 'job' => $input['job_id'],
                'digest' => $input['digest'], 'fingerprint' => $fingerprint, 'metadata' => json_encode($metadata, JSON_THROW_ON_ERROR),
                'content' => $raw, 'uploaded_at' => time(), 'retention_until' => time() + 86400 * 365]);

            return ['id' => $id, 'state' => 'uploaded'];
        });
    }

    /** @return array<string, mixed> */
    public function finalize(string $tenant, string $id): array
    {
        $upload = DB::table('app.evidence_uploads')->where('tenant', $tenant)->where('id', $id)->first();
        abort_if($upload === null, 404);
        abort_unless(hash_equals($upload->digest, hash('sha256', $upload->content)), 409, 'custody_tampered');
        $metadata = json_decode($upload->metadata, true, 32, JSON_THROW_ON_ERROR);
        $binding = $this->authority->binding($tenant, $upload->job);
        foreach (['tenant_id', 'job_id', 'plan_digest', 'digest', 'source_revision', 'evidence_level'] as $key) {
            abort_unless(($binding[$key] ?? null) === $metadata[$key], 409, 'evidence_binding_mismatch');
        }
        $observations = json_decode($upload->content, true, 32, JSON_THROW_ON_ERROR);
        foreach ($observations as $observation) {
            $this->authority->observe($observation);
        }

        return DB::transaction(function () use ($tenant, $id, $upload, $metadata, $binding): array {
            DB::select('SELECT pg_advisory_xact_lock(7604001)');
            $current = DB::table('app.evidence_uploads')->where('id', $id)->first();
            abort_unless($current !== null && hash_equals($upload->content, $current->content) && hash_equals($upload->metadata, $current->metadata), 409, 'custody_changed');
            $receipt = $metadata + ['id' => $id, 'state' => 'finalized', 'native_support' => false, 'scope' => $binding['scope'],
                'producer_actor_id' => $binding['producer_actor_id'], 'requested_by' => $binding['requested_by'],
                'retention_until' => $upload->retention_until, 'finalized_at' => time()];
            $existing = DB::table('app.evidence_records')->where('id', $id)->first();
            if ($existing !== null) {
                return json_decode($existing->receipt, true, 32, JSON_THROW_ON_ERROR);
            }
            DB::table('app.evidence_records')->insert(['id' => $id, 'tenant' => $tenant, 'job' => $upload->job,
                'receipt' => json_encode($receipt, JSON_THROW_ON_ERROR)]);

            return $receipt;
        });
    }

    /** @param array<string, list<string|null>> $headers
     * @return array<string, mixed> */
    public function read(string $tenant, string $id, array $headers): array
    {
        $record = DB::table('app.evidence_records')->where('tenant', $tenant)->where('id', $id)->first();
        abort_if($record === null, 404);
        $receipt = json_decode($record->receipt, true, 32, JSON_THROW_ON_ERROR);
        $this->authority->reader($headers, $tenant, $receipt['scope'], 'evidence.read');
        $raw = DB::table('app.evidence_uploads')->where('id', $id)->value('content');
        abort_unless(is_string($raw) && hash_equals($receipt['digest'], hash('sha256', $raw)), 409, 'custody_tampered');

        return $receipt + ['observations' => json_decode($raw, true, 32, JSON_THROW_ON_ERROR),
            'reviews' => DB::table('app.evidence_reviews')->where('evidence', $id)->orderByDesc('recorded_at')->orderByDesc('id')->limit(1000)->get()->reverse()->values()->all()];
    }

    /** @param array<string, list<string|null>> $headers
     * @return array<string, mixed> */
    public function review(string $tenant, string $id, array $headers, string $decision): array
    {
        $row = DB::table('app.evidence_records')->where('tenant', $tenant)->where('id', $id)->first();
        abort_if($row === null, 404);
        $record = json_decode($row->receipt, true, 32, JSON_THROW_ON_ERROR);
        $actor = $this->authority->reader($headers, $tenant, $record['scope'], 'evidence.review');
        $raw = DB::table('app.evidence_uploads')->where('id', $id)->value('content');
        abort_unless(is_string($raw) && hash_equals($record['digest'], hash('sha256', $raw)), 409, 'custody_tampered');
        abort_if(in_array($actor['actor_id'], [$record['producer_actor_id'], $record['requested_by']], true), 403, 'independent_reviewer_required');
        abort_unless(in_array($decision, ['accepted_simulation', 'rejected'], true), 422);
        $review = ['id' => (string) Str::uuid(), 'evidence' => $id, 'reviewer' => $actor['actor_id'],
            'decision' => $decision, 'recorded_at' => time()];
        DB::table('app.evidence_reviews')->insert($review);

        return $review + ['native_support' => false];
    }
}
