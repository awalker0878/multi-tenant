<?php

declare(strict_types=1);

namespace App\Domain\Support;

final class SupportPolicy
{
    public const VERSION = 1;

    public const MAX_MINUTES = 60;

    public const REVIEW_HOURS = 24;

    /** @var array<string, string> */
    public const ACTIONS = ['support.membership.inspect' => 'membership', 'support.grant.inspect' => 'grant'];

    /** @var list<string> */
    public const TERMINAL = ['rejected', 'revoked', 'expired', 'invalidated'];
}
