<?php

declare(strict_types=1);

namespace App\Application\Evidence\Contracts;

interface EvidenceAuthority
{
    /** @param array<string, list<string|null>> $headers */
    public function producer(array $headers): void;

    /** @return array<string, mixed> */
    public function binding(string $tenant, string $job): array;

    /** @param array<string, mixed> $observation */
    public function observe(array $observation): void;

    /** @param array<string, list<string|null>> $headers
     * @param array<string, mixed> $scope
     * @return array<string, mixed> */
    public function reader(array $headers, string $tenant, array $scope, string $action): array;
}
