<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Application\Messaging\Actions\PublishCatalogueEvent;
use Illuminate\Console\Command;
use Throwable;

final class PublishCatalogueEvents extends Command
{
    protected $signature = 'catalogue:publish-events {--limit=100}';

    protected $description = 'Publish a bounded batch of committed catalogue facts using confirmed delivery';

    public function handle(PublishCatalogueEvent $publish): int
    {
        $limit = $this->option('limit');
        if (! is_string($limit) || ! ctype_digit($limit) || (int) $limit < 1 || (int) $limit > 100) {
            $this->error('Use a limit from 1 to 100.');

            return self::FAILURE;
        }
        $count = 0;
        try {
            while ($count < (int) $limit && $publish->handle()) {
                $count++;
            }
        } catch (Throwable) {
            $this->error('Publication unavailable; unconfirmed events remain pending.');

            return self::FAILURE;
        }
        $this->line(json_encode(['published' => $count], JSON_THROW_ON_ERROR));

        return self::SUCCESS;
    }
}
