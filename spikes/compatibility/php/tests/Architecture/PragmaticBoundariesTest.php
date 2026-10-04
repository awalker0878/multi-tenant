<?php

declare(strict_types=1);

use Illuminate\Database\Eloquent\Model;

/** @return list<class-string> */
function spikeClasses(string $directory): array
{
    $root = dirname(__DIR__, 2).'/app/';
    $path = $root.$directory;

    if (! is_dir($path)) {
        return [];
    }

    $classes = [];
    $files = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($path));

    foreach ($files as $file) {
        if ($file->isFile() && $file->getExtension() === 'php') {
            $classes[] = 'App\\'.str_replace('/', '\\', substr($file->getPathname(), strlen($root), -4));
        }
    }

    sort($classes);

    return $classes;
}

test('the architecture suite inspects implemented spike classes', function () {
    foreach (['Domain', 'Application', 'Http', 'Providers'] as $directory) {
        expect(spikeClasses($directory))->not->toBeEmpty();
    }
});

arch('domain does not depend on orchestration or delivery')
    ->expect('App\\Domain')
    ->not->toUse([
        'App\\Application', 'App\\Infrastructure', 'App\\Http', 'App\\Console',
        'App\\Jobs', 'App\\Listeners', 'App\\Policies', 'App\\Providers',
        'Product\\Contracts', 'Product\\Contexts', 'Product\\Services',
        'Illuminate\\Http', 'Illuminate\\Foundation\\Http', 'Illuminate\\Routing',
        'Illuminate\\Console', 'Illuminate\\Support\\Facades\\Http',
        'Illuminate\\Support\\Facades\\Request', 'Illuminate\\Support\\Facades\\Response',
        'Illuminate\\Support\\Facades\\Route', 'Inertia',
        'Symfony\\Component\\HttpFoundation', 'Symfony\\Component\\HttpClient', 'Psr\\Http',
    ]);

arch('application does not depend on concrete infrastructure or delivery')
    ->expect('App\\Application')
    ->not->toUse([
        'App\\Infrastructure', 'App\\Http', 'App\\Console', 'App\\Jobs',
        'App\\Listeners', 'App\\Policies', 'App\\Providers',
        'Product\\Contracts', 'Product\\Contexts', 'Product\\Services',
        'Illuminate\\Http', 'Illuminate\\Foundation\\Http', 'Illuminate\\Routing',
        'Illuminate\\Console', 'Illuminate\\Support\\Facades\\Http',
        'Illuminate\\Support\\Facades\\Request', 'Illuminate\\Support\\Facades\\Response',
        'Illuminate\\Support\\Facades\\Route', 'Inertia',
        'Symfony\\Component\\HttpFoundation', 'Symfony\\Component\\HttpClient', 'Psr\\Http',
    ]);

test('actions expose a public non-static handle method', function () {
    $actions = array_values(array_filter(
        spikeClasses('Application'),
        fn (string $class): bool => str_contains($class, '\\Actions\\'),
    ));

    expect($actions)->not->toBeEmpty();

    foreach ($actions as $class) {
        $reflection = new ReflectionClass($class);
        expect($reflection->hasMethod('handle'))->toBeTrue();
        $handle = $reflection->getMethod('handle');
        $this->assertTrue($handle->isPublic(), 'Action handle must be public: '.$class);
        expect($handle->isStatic())->toBeFalse();
    }
});

test('domain models may use eloquent under the selected convention', function () {
    $models = array_filter(
        spikeClasses('Domain'),
        fn (string $class): bool => is_subclass_of($class, Model::class),
    );

    expect($models)->not->toBeEmpty();
});

test('the spike resolves only its own application source', function () {
    $manifest = json_decode(file_get_contents(dirname(__DIR__, 2).'/composer.json'), true, 512, JSON_THROW_ON_ERROR);

    expect($manifest['autoload'])->toBe(['psr-4' => ['App\\' => 'app/']])
        ->and($manifest['autoload-dev'])->toBe(['psr-4' => ['Tests\\' => 'tests/']]);
});
