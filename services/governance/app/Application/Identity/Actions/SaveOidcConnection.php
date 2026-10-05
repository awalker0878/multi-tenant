<?php

declare(strict_types=1);

namespace App\Application\Identity\Actions;

use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use App\Domain\Identity\IdentityLedger;
use App\Domain\Identity\OidcConnection;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

final class SaveOidcConnection
{
    public function __construct(private readonly ResolveIdentitySession $resolve) {}

    /** @param array{revision: int, issuer: string, client_id: string, client_secret?: string|null, redirect_uri: string, administrator_subject: string, private_networks: list<string>} $settings
     * @return array<string, mixed>
     */
    public function handle(#[\SensitiveParameter] string $token, #[\SensitiveParameter] array $settings): array
    {
        return DB::transaction(function () use ($token, $settings): array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->resolve->handle($token, requireSetup: true);
            $installation = DB::table('app.oidc_installation')->where('id', 1)->lockForUpdate()->first();
            if ($installation === null || $installation->latest_revision !== $settings['revision']) {
                throw new IdentityDenied('revision_conflict', 409);
            }
            $previous = OidcConnection::query()->find($settings['revision']);
            $secret = $settings['client_secret'] ?? '';
            if ($secret === '' && ($previous === null || $previous->issuer !== $settings['issuer'] || $previous->client_id !== $settings['client_id'])) {
                throw new IdentityDenied('client_secret_required', 422);
            }
            $reference = $previous?->secret_ref;
            if ($secret !== '') {
                $reference = (string) Str::uuid();
                DB::table('app.identity_secrets')->insert(['id' => $reference, 'ciphertext' => Crypt::encryptString($secret), 'created_at' => now()]);
            }
            $revision = $settings['revision'] + 1;
            $connection = new OidcConnection;
            $connection->forceFill([
                'revision' => $revision, 'issuer' => $settings['issuer'], 'client_id' => $settings['client_id'],
                'secret_ref' => $reference, 'redirect_uri' => $settings['redirect_uri'],
                'administrator_subject' => $settings['administrator_subject'], 'private_networks' => $settings['private_networks'], 'created_at' => now(),
            ])->save();
            DB::table('app.oidc_installation')->where('id', 1)->update(['latest_revision' => $revision]);
            IdentityLedger::record('identity.oidc.settings_saved', $actor->toArray()['subject']);

            return $connection->settings();
        });
    }
}
