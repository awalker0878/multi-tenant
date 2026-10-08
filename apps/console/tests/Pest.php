<?php

declare(strict_types=1);

use Tests\TestCase;

require __DIR__.'/Support/NotificationFixture.php';

pest()->extend(TestCase::class)->in('Feature');
