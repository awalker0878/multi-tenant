<?php

declare(strict_types=1);

namespace App\Application\Foundation\Data;

enum DependencyStatus: string
{
    case Ready = 'ready';
    case Unavailable = 'not_ready';
    case Unauthorized = 'unauthorized';
}
