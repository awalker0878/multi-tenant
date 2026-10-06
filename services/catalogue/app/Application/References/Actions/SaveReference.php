<?php

declare(strict_types=1);

namespace App\Application\References\Actions;

use App\Application\Authorization\Contracts\OwnerDirectory;
use App\Application\Authorization\Data\ActorContext;
use App\Domain\IntentRevisions\CanonicalJson;
use App\Domain\IntentRevisions\CommandJournal;
use App\Domain\IntentRevisions\IntentFailure;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

final class SaveReference
{
    public function __construct(private readonly OwnerDirectory $owners) {}

    /**
     * @param array<string,mixed> $definition
     * @return array<string,mixed> */
    public function handle(ActorContext $actor, string $kind, string $key, array $definition, ?string $id = null, ?string $etag = null, bool $retire = false): array
    {
        Gate::forUser($actor)->authorize('catalogue', ['reference.write', $actor->tenantId, null, null]);
        if (! in_array($kind, ['environment', 'wsd', 'security-domain'], true)) {
            throw new IntentFailure('unknown_reference_kind');
        }
        if (! $retire) {
            $fields = ['name', 'owner_id', ...($kind === 'environment' ? [] : ['shareable']), ...($kind === 'security-domain' ? ['zone'] : [])];
            if (array_diff(array_keys($definition), $fields) !== []) {
                throw new IntentFailure('unknown_reference_fields');
            }
            Validator::make($definition, ['name' => ['required', 'string', 'max:200'], 'owner_id' => ['required', 'uuid', 'lowercase'],
                ...($kind === 'environment' ? [] : ['shareable' => ['required', 'boolean']]), ...($kind === 'security-domain' ? ['zone' => ['required', Rule::in(['PAZ', 'OZ', 'RZ', 'HRZ'])]] : [])])->validate();
            $this->owners->assertOwners($actor, [$definition['owner_id']]);
        } elseif ($definition !== []) {
            throw new IntentFailure('retirement_body_must_be_empty');
        }
        $fingerprint = hash('sha256', CanonicalJson::encode([$kind, $id, $etag, $retire, $definition]));

        return DB::transaction(function () use ($actor, $kind, $key, $definition, $id, $etag, $retire, $fingerprint): array {
            DB::statement("SET LOCAL lock_timeout='3s'");
            $retry = CommandJournal::existing($actor->tenantId, $actor->actorId, $key, $fingerprint);
            if ($retry !== null) {
                return $retry;
            }
            $tenant = $actor->tenantId;
            if ($id === null) {
                $id = (string) Str::uuid();
                $version = 1;
                if ($retire || DB::table('app.catalogue_references')->where(['tenant_id' => $tenant, 'kind' => $kind, 'name' => $definition['name']])->exists()) {
                    throw new IntentFailure('reference_name_conflict', 409);
                }
                DB::table('app.catalogue_references')->insert(['id' => $id, 'tenant_id' => $tenant, 'kind' => $kind, 'name' => $definition['name'], 'version' => $version]);
            } else {
                $row = DB::table('app.catalogue_references')->where(['tenant_id' => $tenant, 'id' => $id, 'kind' => $kind])->lockForUpdate()->first();
                if ($row === null) {
                    throw new IntentFailure('not_found', 404);
                }
                if ($etag === null) {
                    throw new IntentFailure('precondition_required', 428, 'etag');
                }
                if ($etag !== '"'.$id.':'.$row->version.'"') {
                    throw new IntentFailure('stale_revision', 412, 'etag');
                }
                if (in_array($row->retired, [true, 1, '1', 't'], true)) {
                    throw new IntentFailure('reference_retired', 409);
                }
                $previous = json_decode(DB::table('app.catalogue_reference_versions')->where(['tenant_id' => $tenant, 'reference_id' => $id, 'version' => $row->version])->value('definition'), true, 512, JSON_THROW_ON_ERROR);
                if ($retire) {
                    if (DB::table('app.catalogue_revision_references as rr')->join('app.catalogue_deployments as d', function ($j): void {
                        $j->on('d.tenant_id', '=', 'rr.tenant_id')->on('d.current_revision_id', '=', 'rr.revision_id');
                    })->where('rr.tenant_id', $tenant)->where('rr.reference_id', $id)->exists()) {
                        throw new IntentFailure('reference_in_use', 409);
                    }
                    $definition = $previous;
                } elseif ($definition['name'] !== $row->name || ($kind === 'security-domain' && $definition['zone'] !== $previous['zone'])) {
                    throw new IntentFailure('reference_identity_is_immutable', 409);
                }
                $version = (int) $row->version + 1;
                DB::table('app.catalogue_references')->where('id', $id)->update(['version' => $version, 'retired' => $retire]);
            }
            DB::table('app.catalogue_reference_versions')->insert(['tenant_id' => $tenant, 'reference_id' => $id, 'version' => $version, 'definition' => CanonicalJson::encode($definition), 'actor_id' => $actor->actorId]);
            CommandJournal::event($tenant, $actor->actorId, $id, $version, $retire ? 'catalogue.reference.retired' : 'catalogue.reference.changed');
            $response = ['id' => $id, 'kind' => $kind, 'version' => $version, 'etag' => '"'.$id.':'.$version.'"', 'retired' => $retire, 'definition' => $definition];
            CommandJournal::complete($tenant,$actor->actorId,$key,$fingerprint,$response);

            return $response;
        });
    }
}
