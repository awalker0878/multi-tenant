<?php

declare(strict_types=1);

test('liveness reports only a running process with no configured service dependencies', function () {
    $this->getJson('/health/live')
        ->assertOk()
        ->assertExactJson(['service' => 'assurance', 'status' => 'alive', 'scope' => 'process'])
        ->assertHeader('Cache-Control', 'no-store, private');
});

test('readiness remains closed until the assurance dependencies are implemented', function () {
    $this->getJson('/health/ready')
        ->assertStatus(503)
        ->assertExactJson([
            'service' => 'assurance',
            'status' => 'not_ready',
            'scope' => 'service',
            'reason' => 'foundation_only',
        ])
        ->assertHeader('Cache-Control', 'no-store, private')
        ->assertHeader('Retry-After', '10');
});

test('health endpoints reject writes', function (string $path) {
    $this->postJson($path, ['tenant_id' => 'untrusted'])->assertStatus(405);
})->with(['/health/live', '/health/ready']);

test('business routes are absent and expose no exception diagnostics', function (string $path) {
    $this->getJson($path)->assertNotFound()
        ->assertJsonMissingPath('exception')
        ->assertJsonMissingPath('file')
        ->assertJsonMissingPath('trace');
})->with(['/v1/tenants/tenant-a/evidence', '/v1/tenants/tenant-a/qualification-decisions', '/v1/tenants/tenant-a/supported-capabilities']);

test('a caller cannot configure readiness or start a browser session through health input', function () {
    $response = $this->withHeaders([
        'Authorization' => 'Bearer synthetic-untrusted',
        'X-Tenant-Id' => 'tenant-b',
        'X-Assurance-Ready' => 'true',
    ])->getJson('/health/ready?ready=true&status=ready');

    $response->assertStatus(503)->assertJsonPath('status', 'not_ready');
    expect($response->headers->has('Set-Cookie'))->toBeFalse();
});

test('unknown routes return JSON even without an accept header', function () {
    $this->get('/unknown')->assertNotFound()->assertHeader('Content-Type', 'application/json');
});
