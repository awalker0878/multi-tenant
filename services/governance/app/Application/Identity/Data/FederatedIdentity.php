<?php

declare(strict_types=1);

namespace App\Application\Identity\Data;

final readonly class FederatedIdentity
{
    public bool $passwordChangeRequired;

    public function __construct(public string $subject, public bool $installationAdministrator)
    {
        $this->passwordChangeRequired = false;
    }

    /** @return array{subject: string, kind: string, password_change_required: bool, permissions: list<string>} */
    public function toArray(): array
    {
        return [
            'subject' => $this->subject, 'kind' => 'federated', 'password_change_required' => false,
            'permissions' => $this->installationAdministrator ? ['identity.setup', 'tenants.create', 'identity.logout'] : ['identity.logout'],
        ];
    }
}
