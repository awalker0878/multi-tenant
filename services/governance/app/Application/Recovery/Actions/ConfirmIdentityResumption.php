<?php

declare(strict_types=1);

namespace App\Application\Recovery\Actions;

use App\Application\Recovery\Contracts\RecoveryCustody;
use App\Application\Recovery\Contracts\RecoveryDatabase;
use App\Application\Recovery\RecoveryResumption;
use App\Application\Support\Contracts\SupportTrust;
use App\Domain\Recovery\RecoveryDenied;
use App\Domain\Recovery\RecoveryJson;
use Illuminate\Support\Facades\DB;

final class ConfirmIdentityResumption
{
    public function __construct(private readonly RecoveryDatabase $database, private readonly RecoveryCustody $custody,
        private readonly RecoveryResumption $resumption, private readonly SupportTrust $trust) {}

    /** @return array<string, mixed> */
    public function handle(string $envelope): array
    {
        if (DB::transactionLevel() !== 0) {
            throw new RecoveryDenied;
        }
        $authorized = $this->custody->authorize($envelope, 'resume');
        $trust = $this->database->observe(fn () => $this->trust->current());

        return DB::transaction(function () use ($authorized, $envelope, $trust): array {
            $this->database->lock();
            $payload = $authorized['payload'];
            if (! is_string($payload['recovery_id'] ?? null) || $trust->connectionRevision !== DB::table('app.oidc_installation')->where('id', 1)->value('active_revision')
                || now()->getTimestamp() - $trust->observedAt > 5) {
                throw new RecoveryDenied;
            }
            $expected = $this->resumption->build($payload['recovery_id'], $payload['created_at'], $payload['expires_at'], $trust->keyThumbprints);
            if (RecoveryJson::encode($payload) !== RecoveryJson::encode($expected)) {
                throw new RecoveryDenied;
            }
            $this->custody->authorize($envelope, 'resume');
            DB::table('app.identity_recovery_releases')->insert(['id' => $payload['recovery_id'], 'envelope_json' => $envelope,
                'envelope_sha256' => hash('sha256', $envelope), 'confirmed_at' => now()]);

            return ['recovery_id' => $payload['recovery_id'], 'envelope_sha256' => hash('sha256', $envelope),
                'post_snapshot_sha256' => $payload['post_snapshot_sha256'], 'admission' => 'HELD_CONFIRMED'];
        });
    }
}
