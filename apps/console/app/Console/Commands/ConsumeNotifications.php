<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Application\Notifications\Actions\ConsumeNotification;
use App\Application\Notifications\Contracts\NotificationSource;
use Illuminate\Console\Command;
use Throwable;

final class ConsumeNotifications extends Command
{
    protected $signature = 'console:consume-notifications {--limit=100}';

    protected $description = 'Durably record a bounded batch of tenant notifications before broker acknowledgement';

    public function handle(ConsumeNotification $consume, NotificationSource $source): int
    {
        $limit = filter_var($this->option('limit'), FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 500]]);
        if ($limit === false) {
            $this->error('Limit must be between 1 and 500.');

            return self::FAILURE;
        }
        $counts = ['recorded' => 0, 'duplicate' => 0, 'quarantined' => 0];
        $failed = false;
        try {
            for ($index = 0; $index < $limit; $index++) {
                $result = $consume->handle();
                if ($result === 'idle') {
                    break;
                }
                $counts[$result]++;
            }
        } catch (Throwable) {
            $failed = true;
        } finally {
            try {
                $source->close();
            } catch (Throwable) {
                $failed = true;
            }
        }
        if ($failed) {
            $this->error('Notification delivery unavailable; unacknowledged messages remain with the broker.');
        }
        $this->line(json_encode($counts, JSON_THROW_ON_ERROR));

        return $failed ? self::FAILURE : self::SUCCESS;
    }
}
