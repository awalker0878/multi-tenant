<?php

declare(strict_types=1);

namespace App\Application\Messaging\Contracts;

interface EventEncoder
{
    public function encode(\stdClass $row): string;
}
