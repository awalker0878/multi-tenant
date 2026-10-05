<?php

declare(strict_types=1);

use App\Application\Support\Contracts\SupportTrust;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Facades\DB;

beforeEach(function (): void {
    initializeFederationFixture($this);
});

afterEach(function (): void {
    unlink($this->credentialFile);
});

it('binds handover and subsequent federated sessions to their verified signing material', function (): void {
    $trust = app(SupportTrust::class)->current();
    $first = DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $this->token))->first();
    expect($trust->keyThumbprints)->toContain($first->provider_key_sha256)
        ->and(strlen($first->provider_key_sha256))->toBe(64);
    $token = federatedLogin($this, 'support-subject');
    expect(DB::table('app.federated_sessions')->where('token_hash', hash('sha256', $token))->value('provider_key_sha256'))
        ->toBe($first->provider_key_sha256);
    expect(json_encode($trust))->not->toContain('synthetic-oidc-secret');
});

it('fails the online support trust check when issuer signing keys or key custody are unavailable', function (string $failure): void {
    if ($failure === 'issuer') {
        $this->provider->unavailable = true;
    } elseif ($failure === 'keys') {
        $this->provider->keyOverride = [];
    } else {
        DB::table('app.identity_secrets')->update(['ciphertext' => 'unreadable-custody']);
    }
    try {
        app(SupportTrust::class)->current();
        test()->fail('Expected fail-closed online support trust');
    } catch (IdentityDenied $error) {
        expect($error->status)->toBe(503)->and($error->reason)->toBe('support_trust_unavailable');
    }
})->with(['issuer', 'keys', 'custody']);
