<?php

declare(strict_types=1);

namespace App\Domain\Catalogue;

use RuntimeException;

final class CatalogueFailure extends RuntimeException
{
    public function __construct(public readonly int $status, public readonly string $reason = 'catalogue_unavailable', public readonly string $field = 'intent')
    {
        parent::__construct('Catalogue request could not be completed.');
    }
}
