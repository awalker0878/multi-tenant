<?php

declare(strict_types=1);

namespace App\Application\Recovery\Actions;

use App\Application\Recovery\Contracts\RecoveryDatabase;
use App\Application\Recovery\RecoveryPlan;
use App\Application\Support\Contracts\SupportTrust;
use App\Domain\Recovery\RecoveryDenied;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class PrepareIdentityRecovery
{
    public function __construct(private readonly RecoveryDatabase $database, private readonly RecoveryPlan $plan, private readonly SupportTrust $trust) {}

    /** @param array<string, mixed> $observations
     * @return array<string, mixed>
     */
    public function handle(array $observations): array
    {
        if (DB::transactionLevel() !== 0) {
            throw new RecoveryDenied;
        }
        // Pinned TLS/discovery/JWKS and key decryption finish before the DB lock.
        $trust = $this->database->observe(fn () => $this->trust->current());

        return DB::transaction(function () use ($observations, $trust): array {
            $this->database->lock();
            if ($trust->connectionRevision !== DB::table('app.oidc_installation')->where('id', 1)->value('active_revision') || now()->getTimestamp() - $trust->observedAt > 5) {
                throw new RecoveryDenied;
            }

            return $this->plan->build($observations, (string) Str::uuid(), now()->getTimestamp(), now()->getTimestamp() + 900, $trust->keyThumbprints);
        });
    }
}
