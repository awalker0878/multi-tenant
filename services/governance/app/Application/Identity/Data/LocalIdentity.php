<?php

declare(strict_types=1);

namespace App\Application\Identity\Data;

final readonly class LocalIdentity
{
    public function __construct(public bool $passwordChangeRequired) {}

    /** @return array{subject: string, password_change_required: bool, permissions: list<string>} */
    public function toArray(): array
    {
        return [
            'subject' => 'bootstrap-admin',
            'password_change_required' => $this->passwordChangeRequired,
            'permissions' => $this->passwordChangeRequired ? ['identity.password.change', 'identity.logout'] : ['identity.setup', 'identity.password.change', 'identity.logout'],
        ];
    }
}
