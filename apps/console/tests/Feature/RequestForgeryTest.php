<?php

declare(strict_types=1);

use Illuminate\Support\Facades\Route;

beforeEach(function (): void {
    // This generic probe complements the actual identity-route CSRF tests.
    Route::middleware('web')->post('/_test/request-forgery', fn () => response()->noContent());
    // Laravel bypasses CSRF in its testing environment. Exercise its real branch.
    $this->app['env'] = 'csrf-check';
});

it('rejects a browser mutation without its session request-forgery token', function (): void {
    $this->post('/_test/request-forgery')->assertStatus(419);
});

it('accepts a matching session token through the same web middleware', function (): void {
    $this->withSession(['_token' => 'console-test-csrf-token'])
        ->post('/_test/request-forgery', ['_token' => 'console-test-csrf-token'])
        ->assertNoContent();
});
