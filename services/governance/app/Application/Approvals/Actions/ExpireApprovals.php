<?php

declare(strict_types=1);

namespace App\Application\Approvals\Actions;

use App\Domain\Approvals\ApprovalExpiry;
use App\Domain\Identity\BootstrapAdministrator;
use Illuminate\Support\Facades\DB;
use InvalidArgumentException;

final class ExpireApprovals
{
    public function handle(int $limit = 100): int
    {
        if ($limit < 1 || $limit > 500) {
            throw new InvalidArgumentException('invalid_batch_limit');
        }
        $count = 0;
        for ($i = 0; $i < $limit; $i++) {
            $changed = DB::transaction(function (): bool {
                // Same lock order as interactive admission/revocation. Expiry is
                // system work and must run even after all actor sessions expire.
                BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
                $row = DB::table('app.approvals')->whereIn('state', ['requested', 'approved'])
                    ->where('expires_at', '<=', now())->orderBy('expires_at')->orderBy('id')->lockForUpdate()->first();

                return $row !== null && ApprovalExpiry::apply($row);
            });
            if (! $changed) {
                break;
            }
            $count++;
        }

        return $count;
    }
}
