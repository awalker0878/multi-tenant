<?php

declare(strict_types=1);

namespace App\Application\Foundation\Contracts;

interface DependencyProbe
{
    public function healthy(): bool;
}
