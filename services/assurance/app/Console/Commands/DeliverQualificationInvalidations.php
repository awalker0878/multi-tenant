<?php

declare(strict_types=1);

namespace App\Console\Commands;

use App\Application\Qualification\Actions\DeliverQualificationInvalidation;
use Illuminate\Console\Command;
use Throwable;

final class DeliverQualificationInvalidations extends Command
{
    protected $signature = 'assurance:deliver-invalidations {--limit=50}';

    protected $description = 'Deliver bounded committed qualification changes with durable receiving receipts';

    public function handle(DeliverQualificationInvalidation $delivery): int
    {
        if (config('planning.qualification_authority_mode') !== 'database') {
            $this->error('qualification_authority_not_commissioned');

            return self::FAILURE;
        }
        $limit = $this->option('limit');
        if (! is_string($limit) || ! ctype_digit($limit) || (int) $limit < 1 || (int) $limit > 100) {
            $this->error('invalid_batch_limit');

            return self::FAILURE;
        }
        $count = 0;
        try {
            while ($count < (int) $limit && $delivery->handle() === 'delivered') {
                $count++;
            }
        } catch (Throwable) {
            // Never log the exception: failed transport messages can include credentials.
            $this->error('invalidation_delivery_unconfirmed');

            return self::FAILURE;
        }

        $this->line(json_encode(['delivered' => $count], JSON_THROW_ON_ERROR));

        return self::SUCCESS;
    }
}
