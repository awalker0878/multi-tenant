<?php

declare(strict_types=1);

use Inertia\Testing\AssertableInertia as Assert;

it('serves the public foundation page with only its declared page props', function (): void {
    $this->get('/')
        ->assertOk()
        ->assertHeader('Content-Type', 'text/html; charset=UTF-8')
        ->assertHeader('X-Content-Type-Options', 'nosniff')
        ->assertHeader('X-Frame-Options', 'DENY')
        ->assertSee('<div id="app"', false)
        ->assertInertia(fn (Assert $page): Assert => $page
            ->component('Foundation')
            ->where('productName', 'Enterprise Workload Mobility and Secure Hosting')
            ->where('implementationState', 'foundation')
            ->missing('actor')
            ->missing('tenant')
            ->missing('credentials'));
});

it('supports Inertia navigation without adding an authenticated identity', function (): void {
    $this->get('/', ['X-Inertia' => 'true'])
        ->assertOk()
        ->assertHeader('X-Inertia', 'true')
        ->assertJsonPath('component', 'Foundation')
        ->assertJsonPath('props.implementationState', 'foundation')
        ->assertJsonPath('url', '/');
});

it('sets a private non-cacheable response and secure server-session cookie', function (): void {
    $response = $this->get('/')->assertOk();
    expect($response->headers->get('Cache-Control'))->toContain('no-store')->toContain('private');
    $cookie = $response->getCookie('console_session');
    expect($cookie)->not->toBeNull();
    expect($cookie->isHttpOnly())->toBeTrue()
        ->and($cookie->isSecure())->toBeTrue()
        ->and($cookie->getSameSite())->toBe('lax');
});

it('exposes no authentication or workload endpoints in the foundation', function (string $path): void {
    $this->get($path, ['Accept' => 'application/json'])->assertNotFound();
})->with(['/login', '/register', '/tenants', '/workloads']);
