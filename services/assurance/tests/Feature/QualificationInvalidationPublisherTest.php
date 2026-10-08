<?php

declare(strict_types=1);

use App\Infrastructure\Foundation\MountedSecret;
use App\Infrastructure\Qualification\ConfirmedHttpInvalidationPublisher;
use Illuminate\Support\Facades\Http;

it('requires a configured HTTPS sink, read-only TLS trust and separate mounted secret', function (): void {
    config([
        'planning.qualification_invalidation_url' => 'http://untrusted.invalid/inbox',
        'planning.qualification_invalidation_ca_file' => null,
        'planning.qualification_invalidation_credential_file' => null,
    ]);
    $publisher = new ConfirmedHttpInvalidationPublisher(new MountedSecret);
    $event = [
        'event_id' => '10000000-0000-4000-8000-000000000001',
        'tenant_id' => '10000000-0000-4000-8000-000000000002',
        'scope_sha256' => str_repeat('a', 64),
        'authority_epoch' => 1,
        'event_sha256' => str_repeat('b', 64),
    ];

    expect(fn () => $publisher->publish($event))
        ->toThrow(RuntimeException::class, 'qualification_invalidation_sink_unavailable');
});

it('rejects merely successful HTTP replies and accepts only the exact durable inbox receipt', function (): void {
    $ca = tempnam(sys_get_temp_dir(), 'authority-ca-');
    $token = tempnam(sys_get_temp_dir(), 'authority-token-');
    try {
        file_put_contents($ca, 'synthetic-trust-file-for-faked-transport');
        file_put_contents($token, str_repeat('x', 64));
        config([
            'planning.qualification_invalidation_url' => 'https://receiving.test/internal/qualification-events',
            'planning.qualification_invalidation_ca_file' => $ca,
            'planning.qualification_invalidation_credential_file' => $token,
        ]);
        $event = [
            'event_id' => '10000000-0000-4000-8000-000000000001',
            'scope_sha256' => str_repeat('a', 64),
            'authority_epoch' => 7,
            'event_sha256' => str_repeat('b', 64),
        ];
        $publisher = new ConfirmedHttpInvalidationPublisher(new MountedSecret);
        Http::fake(['https://receiving.test/*' => Http::response(['persisted' => true], 200)]);
        expect(fn () => $publisher->publish($event))
            ->toThrow(RuntimeException::class, 'qualification_invalidation_unconfirmed');

        Http::fake(['https://receiving.test/*' => Http::response([
            'persisted' => true,
            'event_id' => $event['event_id'],
            'scope_sha256' => $event['scope_sha256'],
            'authority_epoch' => 6,
            'event_sha256' => $event['event_sha256'],
        ], 200)]);
        expect(fn () => $publisher->publish($event))
            ->toThrow(RuntimeException::class, 'qualification_invalidation_unconfirmed');

        Http::fake(['https://receiving.test/*' => Http::response(['persisted' => true] + $event, 200)]);
        $publisher->publish($event);
        // The exact persisted acknowledgement above is required for success.
    } finally {
        unlink($ca);
        unlink($token);
    }
});
