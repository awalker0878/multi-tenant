<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Application\Approvals\Actions\ExpireApprovals;
use Illuminate\Console\Command;
use Throwable;

final class ExpireGovernanceApprovals extends Command
{
    protected $signature = 'governance:expire-approvals {--limit=100}';

    protected $description = 'Record elapsed approval deadlines without requiring an active user';

    public function handle(ExpireApprovals $expire): int
    {
        $limit = filter_var($this->option('limit'), FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 500]]);
        if ($limit === false) {
            $this->error('invalid_batch_limit');

            return self::FAILURE;
        }
        try {
            $this->line(json_encode(['expired' => $expire->handle($limit)], JSON_THROW_ON_ERROR));

            return self::SUCCESS;
        } catch (Throwable) {
            $this->error('approval_expiry_unavailable');

            return self::FAILURE;
        }
    }
}
