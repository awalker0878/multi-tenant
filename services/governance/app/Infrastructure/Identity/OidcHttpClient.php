<?php

declare(strict_types=1);

namespace App\Infrastructure\Identity;

use App\Application\Identity\Contracts\OidcHttpTransport;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\OidcConnection;
use App\Domain\Identity\OidcUrl;
use Symfony\Component\HttpFoundation\IpUtils;

final class OidcHttpClient implements OidcHttpTransport
{
    /** @param array<string, string> $form
     * @return array<string, mixed>
     */
    public function request(OidcConnection $connection, string $url, #[\SensitiveParameter] array $form = []): array
    {
        if (OidcUrl::origin($url) !== OidcUrl::origin($connection->issuer)) {
            throw new IdentityDenied('provider_endpoint_denied', 422);
        }
        $host = (string) parse_url($url, PHP_URL_HOST);
        $port = (int) (parse_url($url, PHP_URL_PORT) ?: 443);
        $addresses = $this->addresses($host);
        if ($addresses === []) {
            throw new IdentityDenied('provider_unavailable', 503);
        }
        foreach ($addresses as $address) {
            if (! $this->permits($address, $connection->private_networks)) {
                throw new IdentityDenied('provider_endpoint_denied', 422);
            }
        }
        $body = '';
        $curl = curl_init($url);
        // Pin a validated address and disable proxies/redirects; DNS rebinding cannot change the peer.
        $address = str_contains($addresses[0], ':') ? '['.$addresses[0].']' : $addresses[0];
        curl_setopt_array($curl, [
            CURLOPT_RESOLVE => [$host.':'.$port.':'.$address], CURLOPT_PROXY => '', CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_PROTOCOLS => CURLPROTO_HTTPS, CURLOPT_CONNECTTIMEOUT => 3, CURLOPT_TIMEOUT => 8,
            CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_HTTPHEADER => ['Accept: application/json'],
            CURLOPT_WRITEFUNCTION => static function ($handle, string $chunk) use (&$body): int {
                if (strlen($body) + strlen($chunk) > 262144) {
                    return 0;
                }
                $body .= $chunk;

                return strlen($chunk);
            },
        ]);
        if ($form !== []) {
            curl_setopt_array($curl, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => http_build_query($form, '', '&', PHP_QUERY_RFC3986)]);
        }
        $ok = curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
        unset($curl);
        if ($ok === false || $status !== 200) {
            throw new IdentityDenied('provider_unavailable', 503);
        }
        try {
            $data = json_decode($body, true, 32, JSON_THROW_ON_ERROR);
        } catch (\JsonException) {
            throw new IdentityDenied('invalid_provider_response', 422);
        }
        if (! is_array($data) || array_is_list($data)) {
            throw new IdentityDenied('invalid_provider_response', 422);
        }

        return $data;
    }

    /** @return list<string> */
    protected function addresses(string $host): array
    {
        $literal = trim($host, '[]');
        if (filter_var($literal, FILTER_VALIDATE_IP)) {
            return [$literal];
        }
        $records = @dns_get_record($host, DNS_A | DNS_AAAA);
        $addresses = [];
        foreach ($records ?: [] as $record) {
            $address = $record['ip'] ?? $record['ipv6'] ?? null;
            if (is_string($address)) {
                $addresses[] = $address;
            }
        }

        return array_values(array_unique($addresses));
    }

    /** @param list<string> $networks */
    public function permits(string $address, array $networks): bool
    {
        if (filter_var($address, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)
            && ! IpUtils::checkIp($address, ['100.64.0.0/10', '192.0.0.0/24', '192.0.2.0/24', '198.18.0.0/15', '198.51.100.0/24', '203.0.113.0/24', '224.0.0.0/4', '240.0.0.0/4', '::ffff:0:0/96', '64:ff9b::/96', '2001::/23', '2002::/16', 'ff00::/8'])) {
            return true;
        }

        // Private enterprise IdPs need an explicit console-managed RFC1918 CIDR.
        // Loopback, link-local, metadata and reserved ranges cannot be opted in.
        return IpUtils::checkIp($address, ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'])
            && $networks !== [] && IpUtils::checkIp($address, $networks);
    }
}
