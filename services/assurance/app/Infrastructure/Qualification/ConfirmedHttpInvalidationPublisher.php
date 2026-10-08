<?php

declare(strict_types=1);

namespace App\Infrastructure\Qualification;

use App\Application\Foundation\Contracts\SecretReader;
use App\Application\Qualification\Contracts\ConfirmedInvalidationPublisher;
use Illuminate\Support\Facades\Http;
use RuntimeException;

/**
 * Send only to a configured HTTPS receiving inbox. The receiver must persist
 * event_id plus monotonic scope/epoch before returning an exact acknowledgment.
 */
final readonly class ConfirmedHttpInvalidationPublisher implements ConfirmedInvalidationPublisher
{
    public function __construct(private SecretReader $secrets) {}

    /** @param array<string, mixed> $event */
    public function publish(array $event): void
    {
        $url = config('planning.qualification_invalidation_url');
        $ca = config('planning.qualification_invalidation_ca_file');
        $token = $this->secrets->read(config('planning.qualification_invalidation_credential_file'));
        $parts = is_string($url) ? parse_url($url) : false;
        if (! is_array($parts)
            || ($parts['scheme'] ?? null) !== 'https'
            || ! is_string($parts['host'] ?? null)
            || ! preg_match('/^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$/D', $parts['host'])
            || isset($parts['user'], $parts['pass'])
            || isset($parts['fragment'])
            || ! is_string($ca)
            || ! str_starts_with($ca, '/')
            || is_link($ca)
            || ! is_file($ca)
            || ! is_readable($ca)
            || ! is_string($token)
            || $token === '') {
            throw new RuntimeException('qualification_invalidation_sink_unavailable');
        }

        $response = Http::withOptions(['verify' => $ca, 'allow_redirects' => false])
            ->connectTimeout(2)->timeout(5)->acceptJson()->withToken($token)
            ->post($url, $event);
        $ack = $response->json();
        if ($response->status() !== 200
            || ! is_array($ack)
            || ($ack['persisted'] ?? null) !== true
            || ($ack['event_id'] ?? null) !== $event['event_id']
            || ($ack['scope_sha256'] ?? null) !== $event['scope_sha256']
            || ($ack['authority_epoch'] ?? null) !== $event['authority_epoch']
            || ($ack['event_sha256'] ?? null) !== $event['event_sha256']) {
            // A mere HTTP 2xx or different event cannot clear an invalidation.
            throw new RuntimeException('qualification_invalidation_unconfirmed');
        }
    }
}
