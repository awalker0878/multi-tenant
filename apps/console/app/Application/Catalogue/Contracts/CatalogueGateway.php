<?php

declare(strict_types=1);

namespace App\Application\Catalogue\Contracts;

interface CatalogueGateway
{
    /** @param array<string,string> $parameters
     * @param  array<string,mixed>  $body
     * @return array<string,mixed>
     */
    public function call(string $session, string $tenant, string $operation, array $parameters = [], array $body = [], ?string $key = null, ?string $etag = null, ?string $environment = null, ?string $cursor = null): array;

    public function permitted(string $session, string $tenant, string $action, ?string $application = null, ?string $environment = null): bool;
}
