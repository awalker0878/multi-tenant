<?php

declare(strict_types=1);

use App\Application\Foundation\Contracts\DependencyProbe;

beforeEach(function () {
    $this->healthTokenFile = tempnam(sys_get_temp_dir(), 'health-probe-');
    $this->healthToken = bin2hex(random_bytes(32));
    file_put_contents($this->healthTokenFile, $this->healthToken."\n");
    config(['foundation.health_token_file' => $this->healthTokenFile]);
});

afterEach(function () {
    if (is_file($this->healthTokenFile)) {
        unlink($this->healthTokenFile);
    }
});

test('unknown or malformed health identities never reach a dependency', function (?string $authorization) {
    $this->mock(DependencyProbe::class)->shouldNotReceive('healthy');
    if ($authorization !== null) {
        $this->withHeader('Authorization', str_replace('TOKEN', $this->healthToken, $authorization));
    }

    $response = $this->getJson('/health/dependencies?ready=true');
    $response->assertStatus(401)
        ->assertExactJson(['service' => 'console', 'status' => 'unauthorized', 'scope' => 'foundation_dependencies'])
        ->assertHeader('WWW-Authenticate', 'Bearer')
        ->assertHeader('Cache-Control', 'no-store, private');
    expect($response->headers->has('Set-Cookie'))->toBeFalse();
})->with([null, 'Bearer short', 'Bearer '.str_repeat('x', 64), 'Basic TOKEN', 'Basic Bearer TOKEN', 'Bearer TOKEN extra']);

test('an absent or malformed mounted identity denies even the formerly valid credential', function (string $mode) {
    $this->mock(DependencyProbe::class)->shouldNotReceive('healthy');
    match ($mode) {
        'absent' => unlink($this->healthTokenFile),
        'empty' => file_put_contents($this->healthTokenFile, ''),
        'multiline' => file_put_contents($this->healthTokenFile, $this->healthToken."\nextra"),
        'oversize' => file_put_contents($this->healthTokenFile, str_repeat('a', 5000)),
    };

    $this->withToken($this->healthToken)->getJson('/health/dependencies')->assertStatus(401);
})->with(['absent', 'empty', 'multiline', 'oversize']);

test('authenticated dependency failure is sanitized and never changes product readiness', function () {
    // Missing DB configuration exercises the real adapter without a database connection.
    config(['foundation.database' => []]);
    $response = $this->withToken($this->healthToken)->getJson('/health/dependencies');
    $response->assertStatus(503)
        ->assertExactJson([
            'service' => 'console',
            'status' => 'not_ready',
            'scope' => 'foundation_dependencies',
            'reason' => 'dependency_unavailable',
        ])->assertHeader('Retry-After', '10');
    expect($response->headers->has('Set-Cookie'))->toBeFalse();
    $this->getJson('/health/ready')->assertStatus(503)->assertJsonPath('reason', 'foundation_only');
    $this->getJson('/health/live')->assertOk();
});

test('successful foundation checks grant only dependency readiness and no business authority', function () {
    // The isolated PostgreSQL campaign separately establishes real database behavior.
    $this->mock(DependencyProbe::class)->shouldReceive('healthy')->once()->andReturnTrue();
    $response = $this->withToken($this->healthToken)->getJson('/health/dependencies');
    $response->assertOk()->assertExactJson([
        'service' => 'console', 'status' => 'ready', 'scope' => 'foundation_dependencies',
    ])->assertHeader('Cache-Control', 'no-store, private');
    expect($response->headers->has('Set-Cookie'))->toBeFalse();
    $this->getJson('/health/ready')->assertStatus(503);
    $this->getJson('/v1/tenants')->assertNotFound();
    $this->postJson('/health/dependencies')->assertStatus(405);
});

test('replacing a credential file revokes the old token without restarting the application', function () {
    $this->mock(DependencyProbe::class)->shouldReceive('healthy')->twice()->andReturnTrue();
    $this->withToken($this->healthToken)->getJson('/health/dependencies')->assertOk();
    $replacement = bin2hex(random_bytes(32));
    file_put_contents($this->healthTokenFile, $replacement);
    $this->withToken($this->healthToken)->getJson('/health/dependencies')->assertStatus(401);
    $this->withToken($replacement)->getJson('/health/dependencies')->assertOk();
});

test('credential paths cannot use a stream wrapper', function () {
    $this->mock(DependencyProbe::class)->shouldNotReceive('healthy');
    config(['foundation.health_token_file' => 'data://text/plain,'.$this->healthToken]);
    $this->withToken($this->healthToken)->getJson('/health/dependencies')->assertStatus(401);
});


test('mounted application key wins and an unavailable file never falls back to the environment key', function () {
    $previousEnv = $_ENV['APP_KEY_FILE'] ?? null;
    $previousServer = $_SERVER['APP_KEY_FILE'] ?? null;
    $expectedKey = 'base64:'.base64_encode(random_bytes(32));
    file_put_contents($this->healthTokenFile, $expectedKey."\n");
    $_ENV['APP_KEY_FILE'] = $this->healthTokenFile;
    $_SERVER['APP_KEY_FILE'] = $this->healthTokenFile;

    try {
        $loaded = require base_path('config/app.php');
        expect($loaded['key'])->toBe($expectedKey);
        unlink($this->healthTokenFile);
        $loaded = require base_path('config/app.php');
        expect($loaded['key'])->toBeNull();
    } finally {
        if ($previousEnv === null) {
            unset($_ENV['APP_KEY_FILE']);
        } else {
            $_ENV['APP_KEY_FILE'] = $previousEnv;
        }
        if ($previousServer === null) {
            unset($_SERVER['APP_KEY_FILE']);
        } else {
            $_SERVER['APP_KEY_FILE'] = $previousServer;
        }
    }
});
