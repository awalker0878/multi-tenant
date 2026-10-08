<?php

declare(strict_types=1);

namespace App\Application\Planning\Contracts;

interface ApprovalGateway
{
    /** @param array<string,mixed> $body
     * @return array<string,mixed> */
    public function request(string $session, string $tenant, array $body, string $key): array;
}
