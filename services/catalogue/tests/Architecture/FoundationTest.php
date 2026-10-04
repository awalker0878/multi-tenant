<?php

declare(strict_types=1);

use App\Http\Controllers\HealthController;
use App\Providers\AppServiceProvider;

test('service autoload exposes only its own application and tests', function () {
    $manifest = json_decode(file_get_contents(dirname(__DIR__, 2).'/composer.json'), true, 512, JSON_THROW_ON_ERROR);

    expect($manifest['name'])->toBe('product/catalogue')
        ->and($manifest['autoload'])->toBe(['psr-4' => ['App\\' => 'app/']])
        ->and($manifest['autoload-dev'])->toBe(['psr-4' => ['Tests\\' => 'tests/']])
        ->and($manifest)->not->toHaveKey('repositories');
});

test('the actual bootstrap classes are loaded from the service source', function () {
    $source = realpath(dirname(__DIR__, 2).'/app').DIRECTORY_SEPARATOR;

    foreach ([HealthController::class, AppServiceProvider::class] as $class) {
        $reflection = new ReflectionClass($class);
        expect($reflection->getFileName())->toStartWith($source);
    }
});

arch('implemented application classes use strict types')->expect('App')->toUseStrictTypes();
arch('implemented application classes are final')->expect('App')->toBeFinal();
arch('delivery does not reference sibling source or frontend transport')
    ->expect('App\\Http')
    ->not->toUse(['Product\\Contexts', 'Product\\Services', 'Inertia']);
