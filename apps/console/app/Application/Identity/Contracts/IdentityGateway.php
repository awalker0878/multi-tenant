<?php

declare(strict_types=1);

namespace App\Application\Identity\Contracts;

use App\Application\Identity\Data\ConsoleActor;
use App\Application\Identity\Data\ConsoleSession;

interface IdentityGateway
{
    public function login(string $username, #[\SensitiveParameter] string $password): ConsoleSession;

    public function current(#[\SensitiveParameter] string $token): ConsoleActor;

    public function changePassword(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $currentPassword, #[\SensitiveParameter] string $password): ConsoleSession;

    public function logout(#[\SensitiveParameter] string $token): void;

    /** @return array<string, mixed> */
    public function settings(#[\SensitiveParameter] string $token): array;

    /** @param array<string, mixed> $settings */
    public function saveSettings(#[\SensitiveParameter] string $token, #[\SensitiveParameter] array $settings): void;

    public function begin(string $purpose, #[\SensitiveParameter] string $binding, #[\SensitiveParameter] string $token): string;

    /** @return ConsoleSession|array{verification_token: string, revision: int} */
    public function callback(#[\SensitiveParameter] string $state, #[\SensitiveParameter] string $binding, #[\SensitiveParameter] string $code, #[\SensitiveParameter] string $token): ConsoleSession|array;

    public function activate(#[\SensitiveParameter] string $token, #[\SensitiveParameter] string $proof): ConsoleSession;
}
