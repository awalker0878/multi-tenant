<?php

declare(strict_types=1);

use Inertia\Testing\AssertableInertia as Assert;

it('boots Laravel and returns an initial Inertia HTML page', function (): void {
    $this->get('/compatibility')
        ->assertOk()
        ->assertHeader('Content-Type', 'text/html; charset=UTF-8')
        ->assertSee('<div id="app"', false)
        ->assertInertia(fn (Assert $page): Assert => $page->component('Compatibility')->where('sampleCount', 0));
});

it('returns Inertia JSON with the component props URL and asset version', function (): void {
    $this->get('/compatibility', ['X-Inertia' => 'true', 'X-Inertia-Version' => 'p00-compatibility-v1'])
        ->assertOk()
        ->assertHeader('X-Inertia', 'true')
        ->assertJsonPath('component', 'Compatibility')
        ->assertJsonPath('props.sampleCount', 0)
        ->assertJsonPath('url', '/compatibility')
        ->assertJsonPath('version', 'p00-compatibility-v1');
});

it('requires a fresh page when the Inertia asset version differs', function (): void {
    $this->get('/compatibility', ['X-Inertia' => 'true', 'X-Inertia-Version' => 'old-version'])
        ->assertStatus(409)
        ->assertHeader('X-Inertia-Location', route('compatibility'));
});

it('redirects web validation errors and shares them through Inertia', function (): void {
    $response = $this->from('/compatibility')->post('/compatibility/validate', ['name' => ''], ['X-Inertia' => 'true'])
        ->assertRedirect('/compatibility')
        ->assertSessionHasErrors('name');

    // Preserve browser session continuity instead of relying on an in-process bag.
    $cookie = $response->getCookie('p00_compatibility_session');
    expect($cookie)->not->toBeNull();

    $this->withCookie($cookie->getName(), $cookie->getValue())
        ->get('/compatibility', ['X-Inertia' => 'true', 'X-Inertia-Version' => 'p00-compatibility-v1'])
        ->assertOk()
        ->assertHeader('X-Inertia', 'true')
        ->assertJsonPath('props.errors.name', 'The name field is required.');
});

it('redirects a valid synthetic form to its Inertia page', function (): void {
    $response = $this->post('/compatibility/validate', ['name' => 'P00 probe'], ['X-Inertia' => 'true'])
        ->assertRedirect('/compatibility')
        ->assertSessionHas('notice', 'Compatibility request accepted');

    $cookie = $response->getCookie('p00_compatibility_session');
    expect($cookie)->not->toBeNull();

    $this->withCookie($cookie->getName(), $cookie->getValue())
        ->get('/compatibility', ['X-Inertia' => 'true', 'X-Inertia-Version' => 'p00-compatibility-v1'])
        ->assertOk()
        ->assertHeader('X-Inertia', 'true')
        ->assertJsonPath('props.notice', 'Compatibility request accepted');
});
