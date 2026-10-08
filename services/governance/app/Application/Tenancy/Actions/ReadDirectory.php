<?php

declare(strict_types=1);

namespace App\Application\Tenancy\Actions;

use App\Domain\Identity\BootstrapAdministrator;
use App\Domain\Identity\IdentityDenied;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Throwable;

final class ReadDirectory
{
    private const PAGE_SIZE = 50;

    public function __construct(private readonly AuthorizeTenant $authority) {}

    /** @return array<string, mixed> */
    public function handle(#[\SensitiveParameter] string $token, ?string $tenant, ?string $cursor): array
    {
        return DB::transaction(function () use ($token, $tenant, $cursor): array {
            BootstrapAdministrator::query()->lockForUpdate()->findOrFail(1);
            $actor = $this->authority->actor($token);
            // Resolve live authority before decoding or using any page position.
            if ($tenant !== null) {
                $this->authority->handle($actor, $tenant, 'membership.manage');
            }
            $binding = hash('sha256', $token.'|'.$actor->subject.'|'.($tenant ?? 'tenant-directory'));
            $after = $cursor === null ? null : $this->position($cursor, $binding);
            $query = $tenant === null
                ? DB::table('app.tenants as t')->join('app.tenant_memberships as m', 'm.tenant_id', '=', 't.id')
                    ->where('m.actor_id', $actor->subject)->where('m.state', 'active')
                    ->where(fn ($q) => $q->whereNull('m.expires_at')->orWhere('m.expires_at', '>', now()))
                : DB::table('app.tenant_memberships as m')->join('app.federated_actors as a', 'a.id', '=', 'm.actor_id')
                    ->where('m.tenant_id', $tenant);
            $column = $tenant === null ? 't.id' : 'm.id';
            if ($after !== null) {
                $query->where($column, '>', $after);
            }
            $columns = $tenant === null
                ? ['t.id', 't.name', 't.state', 't.revision', 'm.role', 'm.site_id', 'm.environment']
                : ['m.id', 'm.tenant_id', 'm.actor_id', 'm.role', 'm.site_id', 'm.environment', 'm.state', 'm.expires_at', 'm.revision', 'a.subject'];
            $rows = $query->orderBy($column)->limit(self::PAGE_SIZE + 1)->get($columns);
            $more = $rows->count() > self::PAGE_SIZE;
            $page = $rows->take(self::PAGE_SIZE);
            $last = $page->last();
            $next = $more && $last !== null ? Crypt::encryptString(json_encode([
                'version' => 1, 'binding' => $binding, 'after' => $last->id,
                'expires' => now()->addMinutes(15)->getTimestamp(),
            ], JSON_THROW_ON_ERROR)) : null;

            return [
                $tenant === null ? 'tenants' : 'memberships' => $page->values()->all(),
                'next_cursor' => $next,
                ...($tenant === null ? ['installation_administrator' => $actor->installationAdministrator] : []),
            ];
        });
    }

    private function position(string $cursor, string $binding): string
    {
        try {
            if ($cursor === '' || strlen($cursor) > 2048) {
                throw new IdentityDenied('invalid_cursor', 422);
            }
            $value = json_decode(Crypt::decryptString($cursor), true, 8, JSON_THROW_ON_ERROR);
            if (! is_array($value) || ($value['version'] ?? null) !== 1
                || ! is_string($value['binding'] ?? null) || ! hash_equals($binding, $value['binding'])
                || ! is_string($value['after'] ?? null) || ! Str::isUuid($value['after'])
                || ! is_int($value['expires'] ?? null) || $value['expires'] <= now()->getTimestamp()) {
                throw new IdentityDenied('invalid_cursor', 422);
            }

            return $value['after'];
        } catch (Throwable) {
            throw new IdentityDenied('invalid_cursor', 422);
        }
    }
}
