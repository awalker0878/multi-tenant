<?php

declare(strict_types=1);

namespace Tests;

use App\Domain\Compatibility\Models\Actor;
use App\Domain\Compatibility\Models\Sample;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\Schema;

abstract class TestCase extends BaseTestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        $this->assertTrue(
            $this->app->environment('testing'),
            'HTTP kernel tests require APP_ENV=testing; browser serving uses a separate local process.',
        );

        // HTTP-kernel tests do not claim that JavaScript executes; browser CI does.
        $this->withoutVite();

        Schema::create('compatibility_samples', function (Blueprint $table): void {
            $table->id();
            $table->string('tenant_id');
            $table->string('status');
            $table->unsignedInteger('revision');
        });
        Schema::create('compatibility_audits', function (Blueprint $table): void {
            $table->id();
            $table->foreignId('sample_id')->constrained('compatibility_samples');
            $table->unsignedInteger('revision');
            $table->unsignedInteger('actor_id');
            $table->unique(['sample_id', 'revision']);
        });
    }

    public function actor(string $tenant = 'tenant-a', string $role = 'editor'): Actor
    {
        return new Actor(['id' => 100, 'tenant_id' => $tenant, 'role' => $role]);
    }

    public function sample(string $tenant = 'tenant-a'): Sample
    {
        return Sample::query()->create(['tenant_id' => $tenant, 'status' => 'pending', 'revision' => 1]);
    }
}
