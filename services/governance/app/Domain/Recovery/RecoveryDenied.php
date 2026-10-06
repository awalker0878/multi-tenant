<?php

declare(strict_types=1);

namespace App\Domain\Recovery;

final class RecoveryDenied extends \RuntimeException
{
    public function __construct()
    {
        parent::__construct('identity_recovery_held');
    }
}
