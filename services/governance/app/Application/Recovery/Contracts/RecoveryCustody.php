<?php

declare(strict_types=1);

namespace App\Application\Recovery\Contracts;

use App\Domain\Recovery\RecoveryContext;

interface RecoveryCustody
{
    public function held(): RecoveryContext;

    /** @return array{payload: array<string, mixed>, principals: list<string>} */
    public function authorize(string $envelope, string $purpose): array;
}
