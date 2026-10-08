<?php

declare(strict_types=1);

namespace App\Application\Notifications\Data;

use SensitiveParameter;

final readonly class Delivery
{
    public function __construct(
        #[SensitiveParameter] public string $wire,
        public string $messageId,
        public string $routingKey,
        public string $publisher,
        public string $contentType,
        public bool $truncated = false,
    ) {}
}
