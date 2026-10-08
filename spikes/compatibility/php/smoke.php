<?php

declare(strict_types=1);

require __DIR__.'/vendor/autoload.php';

use Composer\InstalledVersions;
use Illuminate\Database\Capsule\Manager;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Schema\Blueprint;
use Inertia\ResponseFactory;

// Synthetic local model: probes Eloquent, transactions and the SQLite driver.
final class CompatibilitySample extends Model
{
    protected $table = 'compatibility_samples';

    public $timestamps = false;

    protected $guarded = [];
}

$database = new Manager;
$database->addConnection(['driver' => 'sqlite', 'database' => ':memory:']);
$database->setAsGlobal();
$database->bootEloquent();
$database->schema()->create('compatibility_samples', function (Blueprint $table): void {
    $table->id();
    $table->unsignedInteger('revision');
});
$database->getConnection()->transaction(function (): void {
    CompatibilitySample::query()->create(['revision' => 1]);
});
if (CompatibilitySample::query()->count() !== 1) {
    throw new RuntimeException('Committed write missing');
}
try {
    $database->getConnection()->transaction(function (): void {
        CompatibilitySample::query()->create(['revision' => 2]);
        throw new RuntimeException('Intentional rollback');
    });
} catch (RuntimeException $exception) {
    if ($exception->getMessage() !== 'Intentional rollback') {
        throw $exception;
    }
}
if (CompatibilitySample::query()->count() !== 1 || ! class_exists(ResponseFactory::class)) {
    throw new RuntimeException('Rollback or Inertia autoload probe failed');
}
echo json_encode([
    'result' => 'PASS',
    'php' => PHP_VERSION,
    'laravel' => InstalledVersions::getPrettyVersion('laravel/framework'),
    'inertia' => InstalledVersions::getPrettyVersion('inertiajs/inertia-laravel'),
], JSON_THROW_ON_ERROR).PHP_EOL;
