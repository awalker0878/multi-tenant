<?php

declare(strict_types=1);

use App\Application\Authorization\Contracts\OwnerDirectory;
use App\Application\Authorization\Data\ActorContext;
use App\Application\References\Actions\SaveReference;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;

it('rejects nonboolean sharing flags before storing a reference with an invalid published type', function (string $kind, mixed $shareable): void {
    $actor = new ActorContext((string) Str::uuid(), (string) Str::uuid(), 'reference.write',
        ['site_id' => null, 'environment' => null, 'resource_id' => null], (string) Str::uuid());
    $this->mock(OwnerDirectory::class)->shouldNotReceive('assertOwners');
    $definition = ['name' => 'Restricted', 'owner_id' => $actor->actorId, 'shareable' => $shareable,
        ...($kind === 'security-domain' ? ['zone' => 'RZ'] : [])];

    try {
        app(SaveReference::class)->handle($actor, $kind, (string) Str::uuid(), $definition);
        $this->fail('A nonboolean sharing flag was accepted.');
    } catch (ValidationException $error) {
        expect(array_keys($error->errors()))->toBe(['shareable']);
    }
})->with(['wsd', 'security-domain'])->with([0, 1, '0', '1']);
