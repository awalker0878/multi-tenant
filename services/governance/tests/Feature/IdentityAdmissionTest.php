<?php

declare(strict_types=1);

use App\Application\Identity\Actions\BootstrapAdministrator;
use App\Application\Identity\Actions\ResolveIdentitySession;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    initializeIdentityFixture($this);
});

afterEach(function (): void {
    unlink($this->credentialFile);
});

it('binds bootstrap to external custody once and keeps the binding when bootstrap permission is withdrawn', function (): void {
    $binding = DB::table('app.identity_admission')->value('binding_sha256');
    expect($binding)->toBe(hash('sha256', $this->admission['installation_id'].':'.$this->admission['epoch']))
        ->and(app(BootstrapAdministrator::class)->handle())->toBeNull();
    $this->admission['bootstrap_allowed'] = false;
    file_put_contents($this->admissionFile, json_encode($this->admission));
    localLogin($this);
    expect(DB::table('app.identity_admission')->value('binding_sha256'))->toBe($binding);
});

it('fails closed for missing malformed held or changed external custody without caching authority', function (string $condition): void {
    $token = localLogin($this);
    if ($condition === 'missing') {
        unlink($this->admissionFile);
    } elseif ($condition === 'malformed') {
        file_put_contents($this->admissionFile, '{"state":"active"}');
    } else {
        $value = $this->admission;
        match ($condition) {
            'held' => $value['state'] = 'held',
            'epoch' => $value['epoch'] = bin2hex(random_bytes(32)),
            'installation' => $value['installation_id'] = '550e8400-e29b-41d4-a716-446655440099',
        };
        file_put_contents($this->admissionFile, json_encode($value));
    }
    $this->withHeader('X-Console-Session', $token)->getJson('/identity/session')->assertStatus(503)
        ->assertExactJson(['error' => 'identity_recovery_required'])->assertHeader('Cache-Control', 'no-store, private');
    $this->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => $this->temporary])->assertStatus(503);
    $this->postJson('/identity/oidc/flows', ['purpose' => 'login', 'browser_binding' => str_repeat('a', 64)])->assertStatus(503);
    expect(fn () => app(ResolveIdentitySession::class)->handle($token))->toThrow(IdentityDenied::class)
        ->and(fn () => app(BootstrapAdministrator::class)->handle())->toThrow(IdentityDenied::class);
})->with(['missing', 'malformed', 'held', 'epoch', 'installation']);

it('never adopts a restored initialized database or recreates an administrator under new recovery custody', function (): void {
    $token = localLogin($this);
    $oldBinding = DB::table('app.identity_admission')->value('binding_sha256');
    $this->admission['epoch'] = bin2hex(random_bytes(32));
    $this->admission['bootstrap_allowed'] = false;
    file_put_contents($this->admissionFile, json_encode($this->admission));
    expect(fn () => app(BootstrapAdministrator::class)->handle())->toThrow(IdentityDenied::class)
        ->and(DB::table('app.identity_admission')->value('binding_sha256'))->toBe($oldBinding)
        ->and(fn () => app(ResolveIdentitySession::class)->handle($token))->toThrow(IdentityDenied::class);
    DB::table('app.bootstrap_administrator')->update(['state' => 'uninitialized', 'password_hash' => null]);
    DB::table('app.identity_admission')->update(['binding_sha256' => null]);
    expect(fn () => app(BootstrapAdministrator::class)->handle())->toThrow(IdentityDenied::class)
        ->and(DB::table('app.identity_admission')->value('binding_sha256'))->toBeNull()
        ->and(DB::table('app.bootstrap_administrator')->value('state'))->toBe('uninitialized');
});

it('cannot initialize admission through a direct request or adopt an existing installation', function (): void {
    DB::table('app.identity_admission')->update(['binding_sha256' => null]);
    $this->postJson('/identity/local-sessions', ['username' => 'admin', 'password' => $this->temporary])->assertStatus(503);
    expect(fn () => app(BootstrapAdministrator::class)->handle())->toThrow(IdentityDenied::class)
        ->and(DB::table('app.identity_admission')->value('binding_sha256'))->toBeNull();
});
