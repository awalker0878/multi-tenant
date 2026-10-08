<?php

declare(strict_types=1);

namespace App\Application\Recovery\Actions;

use App\Application\Recovery\Contracts\RecoveryDatabase;
use App\Application\Recovery\RecoveryResumption;
use App\Application\Support\Contracts\SupportTrust;
use App\Domain\Recovery\RecoveryDenied;
use Illuminate\Support\Facades\DB;

final class PrepareIdentityResumption
{
    public function __construct(private readonly RecoveryDatabase $database, private readonly RecoveryResumption $resumption, private readonly SupportTrust $trust) {}

    /** @return array<string, mixed> */
    public function handle(string $id): array
    {
        if (DB::transactionLevel() !== 0) {
            throw new RecoveryDenied;
        }
        $trust = $this->database->observe(fn () => $this->trust->current());

        return DB::transaction(function () use ($id, $trust): array {
            $this->database->lock();
            if ($trust->connectionRevision !== DB::table('app.oidc_installation')->where('id', 1)->value('active_revision') || now()->getTimestamp() - $trust->observedAt > 5) {
                throw new RecoveryDenied;
            }

            return $this->resumption->build($id, now()->getTimestamp(), now()->getTimestamp() + 900, $trust->keyThumbprints);
        });
    }
}
