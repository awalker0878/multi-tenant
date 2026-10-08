<?php

declare(strict_types=1);

namespace App\Application\Support\Actions;

use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Support\SupportExpiry;
use Illuminate\Support\Facades\DB;

final class ExpireSupportAccess
{
    public function handle(int $limit = 100): int
    {
        if ($limit < 1 || $limit > 500) {
            throw new \InvalidArgumentException('invalid_batch_limit');
        }
        $ids = DB::table('app.support_requests')->whereIn('state', ['requested', 'approved', 'active'])
            ->where(fn ($q) => $q->where('expires_at', '<=', now())->orWhere('effective_until', '<=', now()))
            ->orderBy('expires_at')->orderBy('id')->limit($limit)->pluck('id');
        $count = 0;
        foreach ($ids as $id) {
            $count += DB::transaction(function () use ($id): int {
                BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
                $row = DB::table('app.support_requests')->where('id', $id)->lockForUpdate()->first();
                if ($row === null) {
                    return 0;
                }
                $before = $row->state;
                SupportExpiry::apply($row);

                return (int) ($before !== $row->state);
            });
        }

        return $count;
    }
}
