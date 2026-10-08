<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Application\Support\Actions\ExpireSupportAccess as Expire;
use Illuminate\Console\Command;
use Throwable;

final class ExpireSupportAccess extends Command
{
    protected $signature = 'support:expire-access {--limit=100}';

    protected $description = 'Record bounded support expiry facts; admission independently checks deadlines';

    public function handle(Expire $expire): int
    {
        $limit = filter_var($this->option('limit'), FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 500]]);
        if ($limit === false) {
            $this->error('invalid_batch_limit');

            return self::FAILURE;
        }
        try {
            $this->line(json_encode(['expired' => $expire->handle($limit)], JSON_THROW_ON_ERROR));
        } catch (Throwable) {
            $this->error('support_expiry_unavailable');

            return self::FAILURE;
        }

        return self::SUCCESS;
    }
}
