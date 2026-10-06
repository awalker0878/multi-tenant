<?php

declare(strict_types=1);

namespace App\Application\IntentRevisions\Actions;

use App\Application\Authorization\Contracts\OwnerDirectory;
use App\Application\Authorization\Data\ActorContext;
use App\Application\IntentRevisions\Contracts\IntentValidator;
use App\Domain\Applications\Models\Application;
use App\Domain\IntentRevisions\CanonicalJson;
use App\Domain\IntentRevisions\CommandJournal;
use App\Domain\IntentRevisions\IntentDocument;
use App\Domain\IntentRevisions\IntentFailure;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Support\Str;

final class PublishIntent
{
    public function __construct(private readonly IntentValidator $validator, private readonly OwnerDirectory $owners) {}

    /**
     * @param array<string,mixed> $intent
     * @return array<string,mixed> */
    public function handle(ActorContext $actor, string $key, array $intent, ?string $applicationId = null, ?string $etag = null, ?string $name = null): array
    {
        $this->validator->validate($intent);
        IntentDocument::check($intent);
        Gate::forUser($actor)->authorize('catalogue', ['application.write', $actor->tenantId, $applicationId, $intent['environment']['id']]);
        $owners = [$intent['service_owner_id'], ...array_column($intent['datasets'], 'owner_id'), ...array_column($intent['services'], 'owner_id')];
        $this->owners->assertOwners($actor, array_values(array_unique($owners)));
        $fingerprint = hash('sha256', CanonicalJson::encode(['intent' => $intent, 'application' => $applicationId, 'etag' => $etag, 'name' => $name, 'action' => 'publish']));

        return DB::transaction(function () use ($actor, $key, $intent, $applicationId, $etag, $name, $fingerprint): array {
            DB::statement("SET LOCAL statement_timeout='5s'");
            DB::statement("SET LOCAL lock_timeout='3s'");
            $retry = CommandJournal::existing($actor->tenantId, $actor->actorId, $key, $fingerprint);
            if ($retry !== null) {
                return $retry;
            }
            $tenant = $actor->tenantId;
            if ($applicationId === null) {
                if (! is_string($name) || trim($name) === '' || mb_strlen($name) > 200) {
                    throw new IntentFailure('application_name_required', 422, 'name');
                }
                $application = new Application;
                $application->id = (string) Str::uuid();
                $application->tenant_id = $tenant;
                $application->name = $name;
                $application->version = 1;
                $application->save();
            } else {
                $application = Application::query()->where('tenant_id', $tenant)->whereKey($applicationId)->lockForUpdate()->first();
                if ($application === null) {
                    throw new IntentFailure('not_found', 404);
                }
                if ($etag === null) {
                    throw new IntentFailure('precondition_required', 428, 'etag');
                }
                if ($etag !== self::etag((string) $application->id, (int) $application->version)) {
                    throw new IntentFailure('stale_revision', 412, 'etag');
                }
                $application->version = (int) $application->version + 1;
                $application->save();
            }
            $id = (string) $application->id;
            $version = (int) $application->version;
            $references = [$intent['environment']['id'] => ['kind' => 'environment', ...$intent['environment']]];
            foreach ($intent['workloads'] as $w) {
                foreach (['wsd' => 'wsd', 'security_domain' => 'security-domain'] as $field => $kind) {
                    $ref = $w[$field];
                    if (isset($references[$ref['id']]) && ($references[$ref['id']]['kind'] !== $kind || $references[$ref['id']]['version'] !== $ref['version'])) {
                        throw new IntentFailure('inconsistent_reference');
                    }
                    $references[$ref['id']] = ['kind' => $kind, ...$ref];
                }
            }
            ksort($references);
            foreach ($references as $ref) {
                $row = DB::table('app.catalogue_references')->where('tenant_id', $tenant)->where('id', $ref['id'])->lockForUpdate()->first();
                if ($row === null || $row->kind !== $ref['kind'] || in_array($row->retired, [true, 1, '1', 't'], true) || (int) $row->version !== $ref['version']) {
                    throw new IntentFailure('reference_unavailable_or_stale');
                }
                $definition = json_decode(DB::table('app.catalogue_reference_versions')->where(['tenant_id' => $tenant, 'reference_id' => $ref['id'], 'version' => $ref['version']])->value('definition'), true, 512, JSON_THROW_ON_ERROR);
                if ($ref['kind'] !== 'environment' && ! $definition['shareable'] && DB::table('app.catalogue_revision_references as rr')->join('app.catalogue_deployments as d', function ($j): void {
                    $j->on('d.tenant_id', '=', 'rr.tenant_id')->on('d.current_revision_id', '=', 'rr.revision_id');
                })->where('rr.tenant_id', $tenant)->where('rr.reference_id', $ref['id'])->where('rr.application_id', '!=', $id)->exists()) {
                    throw new IntentFailure('reference_sharing_not_authorized');
                }
            }
            foreach ($intent['workloads'] as $workload) {
                DB::table('app.catalogue_workloads')->insertOrIgnore(['tenant_id' => $tenant, 'id' => $workload['id'], 'application_id' => $id]);
                if (DB::table('app.catalogue_workloads')->where('tenant_id', $tenant)->where('id', $workload['id'])->value('application_id') !== $id) {
                    throw new IntentFailure('workload_owned_by_another_application');
                }
            }
            $deployment = DB::table('app.catalogue_deployments')->where('tenant_id', $tenant)->where('id', $intent['deployment_id'])->first();
            if ($deployment === null) {
                if (DB::table('app.catalogue_deployments')->where(['tenant_id' => $tenant, 'application_id' => $id])->count() >= 100) {
                    throw new IntentFailure('deployment_limit', 422);
                }
                if (DB::table('app.catalogue_deployments')->where(['tenant_id' => $tenant, 'application_id' => $id, 'environment_id' => $intent['environment']['id']])->exists()) {
                    throw new IntentFailure('deployment_environment_conflict', 409);
                }
                DB::table('app.catalogue_deployments')->insert(['tenant_id' => $tenant, 'id' => $intent['deployment_id'], 'application_id' => $id, 'environment_id' => $intent['environment']['id']]);
            } elseif ($deployment->application_id !== $id || $deployment->environment_id !== $intent['environment']['id']) {
                throw new IntentFailure('deployment_scope_conflict', 409);
            }
            $revision = (string) Str::uuid();
            $canonical = CanonicalJson::encode($intent);
            $digest = hash('sha256', $canonical);
            DB::table('app.catalogue_revisions')->insert(['id' => $revision, 'tenant_id' => $tenant, 'application_id' => $id, 'deployment_id' => $intent['deployment_id'], 'sequence' => $version, 'parent_id' => $deployment?->current_revision_id, 'actor_id' => $actor->actorId, 'digest' => $digest, 'canonical_intent' => $canonical]);
            foreach ($references as $ref) {
                DB::table('app.catalogue_revision_references')->insert(['tenant_id' => $tenant, 'application_id' => $id, 'revision_id' => $revision, 'reference_id' => $ref['id'], 'reference_version' => $ref['version']]);
            }
            foreach ($intent['workloads'] as $w) {
                DB::table('app.catalogue_revision_workloads')->insert(['tenant_id' => $tenant, 'application_id' => $id, 'revision_id' => $revision, 'workload_id' => $w['id']]);
            }
            DB::table('app.catalogue_deployments')->where(['tenant_id' => $tenant, 'id' => $intent['deployment_id']])->update(['current_revision_id' => $revision]);
            CommandJournal::event($tenant, $actor->actorId, $id, $version, $version === 1 ? 'catalogue.application.created' : 'catalogue.intent-revision.created', $revision, $digest);
            $response = ['application_id' => $id, 'revision_id' => $revision, 'deployment_id' => $intent['deployment_id'], 'digest' => $digest, 'etag' => self::etag($id, $version), 'sequence' => $version];
            CommandJournal::complete($tenant, $actor->actorId, $key, $fingerprint, $response);

            return $response;
        });
    }

    public static function etag(string $id, int $version): string
    {
        return '"'.$id.':'.$version.'"';
    }
}
