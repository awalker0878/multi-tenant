<?php

declare(strict_types=1);

namespace App\Infrastructure\Planning;

use App\Application\Planning\Contracts\ApprovalGateway;
use App\Infrastructure\Governance\GovernanceClient;

final class GovernanceApprovals implements ApprovalGateway
{
    public function __construct(private readonly GovernanceClient $governance) {}

    public function request(string $session, string $tenant, array $body, string $key): array
    {
        return $this->governance->send('POST', '/v1/tenants/'.$tenant.'/approvals', $session, $body, $key);
    }
}
