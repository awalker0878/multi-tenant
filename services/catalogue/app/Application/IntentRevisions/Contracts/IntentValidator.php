<?php

declare(strict_types=1);

namespace App\Application\IntentRevisions\Contracts;

interface IntentValidator
{
    /**
     * @param array<string,mixed> $intent */
    public function validate(array $intent): void;
}
