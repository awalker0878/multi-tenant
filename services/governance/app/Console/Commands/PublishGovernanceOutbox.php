<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Application\Messaging\Actions\PublishGovernanceEvent;
use Illuminate\Console\Command;
use Throwable;

final class PublishGovernanceOutbox extends Command
{
    protected $signature = 'governance:publish-outbox {--limit=100}';

    protected $description = 'Publish a bounded batch of committed Governance notifications';

    public function handle(PublishGovernanceEvent $publish): int
    {
        $limit = filter_var($this->option('limit'), FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 500]]);
        if ($limit === false) {
            $this->error('invalid_batch_limit');

            return self::FAILURE;
        }
        $counts = ['published' => 0, 'retry' => 0, 'quarantined' => 0];
        try {
            for ($i = 0; $i < $limit; $i++) {
                $result = $publish->handle();
                if ($result === 'idle') {
                    break;
                }
                $counts[$result]++;
            }
        } catch (Throwable) {
            $this->error('outbox_unavailable');

            return self::FAILURE;
        }
        $this->line(json_encode($counts, JSON_THROW_ON_ERROR));

        return $counts['retry'] + $counts['quarantined'] > 0 ? self::FAILURE : self::SUCCESS;
    }
}
