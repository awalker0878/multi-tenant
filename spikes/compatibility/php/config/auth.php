<?php

declare(strict_types=1);

use App\Domain\Compatibility\Models\Actor;

return [
    'defaults' => ['guard' => 'web', 'passwords' => 'actors'],
    'guards' => ['web' => ['driver' => 'session', 'provider' => 'actors']],
    'providers' => ['actors' => ['driver' => 'eloquent', 'model' => Actor::class]],
];
