<?php

declare(strict_types=1);

use Illuminate\Http\Client\Request as OutboundRequest;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia as Assert;

beforeEach(function (): void {
    $this->credentialFile = tempnam(sys_get_temp_dir(), 'p02-console-');
    file_put_contents($this->credentialFile, bin2hex(random_bytes(32)));
    config(['identity.governance_url' => 'https://governance.example.test', 'identity.credential_file' => $this->credentialFile]);
    Http::preventStrayRequests();
    $this->local = ['identity' => ['subject' => 'bootstrap-admin', 'password_change_required' => false]];
    $this->federated = ['identity' => ['kind' => 'federated', 'subject' => '550e8400-e29b-41d4-a716-446655440000',
        'password_change_required' => false, 'permissions' => ['identity.setup', 'identity.logout']], 'session_token' => str_repeat('b', 64)];
    $this->withSession(['identity.token' => str_repeat('a', 64)]);
});

afterEach(function (): void {
    unlink($this->credentialFile);
});

it('projects only permitted settings and keeps proof and secrets out of page props', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->local),
        'governance.example.test/identity/oidc' => Http::response(['revision' => 1, 'active_revision' => null,
            'settings' => ['issuer' => 'https://idp.example.test', 'client_id' => 'client', 'client_secret' => 'must-never-return',
                'secret_ref' => 'private-custody', 'administrator_subject' => 'admin-sub', 'private_networks' => [], 'secret_configured' => true]]),
    ]);
    $this->withSession(['oidc.proof' => str_repeat('c', 64), 'oidc.proof_revision' => 1])->get('/setup')->assertOk()
        ->assertInertia(fn (Assert $page): Assert => $page->component('identity/Setup')->where('verified', true)
            ->missing('settings.client_secret')->missing('settings.secret_ref')->missing('verification_token')->missing('session_token'));
});

it('never flashes a client secret and does not accept a browser-supplied callback URL', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->local),
        'governance.example.test/identity/oidc' => Http::response(['error' => 'bad settings'], 422),
    ]);
    $this->from('/setup')->put('/setup', ['revision' => 0, 'issuer' => 'https://idp.example.test', 'client_id' => 'client',
        'client_secret' => 'secret-input-must-not-flash', 'administrator_subject' => 'subject', 'private_networks' => [],
        'redirect_uri' => 'https://attacker.example.test/identity/callback'])->assertRedirect('/setup')->assertSessionHasErrors('settings')
        ->assertSessionMissing('_old_input.client_secret');
    Http::assertSent(fn (OutboundRequest $request): bool => $request->method() === 'PUT'
        && $request['redirect_uri'] === rtrim(config('app.url'), '/').'/identity/callback');
});

it('consumes its browser binding and stores successful verification only in the server session', function (): void {
    Http::fake(['governance.example.test/identity/oidc/callback' => Http::response(['verification_token' => str_repeat('c', 64), 'revision' => 1])]);
    $this->withSession(['oidc.binding' => str_repeat('d', 64), 'oidc.purpose' => 'setup'])
        ->get('/identity/callback?state='.str_repeat('e', 64).'&code=one-use-code')->assertRedirect('/setup')
        ->assertSessionHas('oidc.proof', str_repeat('c', 64))->assertSessionMissing('oidc.binding');
    $this->get('/identity/callback?state='.str_repeat('e', 64).'&code=one-use-code')->assertRedirect('/login');
    Http::assertSentCount(1);
});

it('requires the server-held proof then rotates the entire session on activation', function (): void {
    Http::fake([
        'governance.example.test/identity/session' => Http::response($this->local),
        'governance.example.test/identity/oidc/activation' => Http::response($this->federated),
    ]);
    $this->from('/setup')->post('/setup/activate', ['verification_token' => str_repeat('c', 64)])->assertSessionHasErrors('settings');
    $this->withSession(['oidc.proof' => str_repeat('c', 64), '_token' => 'old-token', 'private-old-page' => 'clear-me']);
    $oldId = session()->getId();
    $this->post('/setup/activate')->assertRedirect('/setup')->assertSessionHas('identity.token', str_repeat('b', 64))
        ->assertSessionMissing('oidc')->assertSessionMissing('private-old-page');
    expect(session()->getId())->not->toBe($oldId)->and(session()->token())->not->toBe('old-token');
});

it('preserves local access on failed callback and never reflects provider error contents', function (): void {
    Http::fake(['governance.example.test/identity/oidc/callback' => Http::response(['error' => 'private-provider-data'], 401)]);
    $this->withSession(['oidc.binding' => str_repeat('d', 64), 'oidc.purpose' => 'setup'])
        ->get('/identity/callback?state='.str_repeat('e', 64).'&code=private-code')->assertRedirect('/setup')
        ->assertSessionHas('identity.token', str_repeat('a', 64))->assertSessionMissing('oidc.proof');
    expect(json_encode(session()->all()))->not->toContain('private-provider-data')->not->toContain('private-code');
});

it('requires real CSRF on provider settings test activation and sign-in', function (string $method, string $path): void {
    $this->app['env'] = 'csrf-check';
    Http::fake();
    $this->call($method, $path)->assertStatus(419);
    Http::assertNothingSent();
})->with([['PUT', '/setup'], ['POST', '/setup/test'], ['POST', '/setup/activate'], ['POST', '/identity/sign-in']]);
