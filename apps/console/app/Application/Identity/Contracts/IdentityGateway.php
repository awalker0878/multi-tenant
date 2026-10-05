<?php

declare(strict_types=1);

namespace App\Application\Identity\Contracts;

use App\Application\Identity\Data\LocalActor;
use App\Application\Identity\Data\LocalSession;

interface IdentityGateway
{
    public function login(string $username, #[\SensitiveParameter] string $password): LocalSession;

    public function current(#[\SensitiveParameter] string $token): LocalActor;

    public function changePassword(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $currentPassword, #[\SensitiveParameter] string $password): LocalSession;

    public function logout(#[\SensitiveParameter] string $token): void;
}
