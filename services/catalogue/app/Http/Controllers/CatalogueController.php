<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Authorization\Data\ActorContext;
use App\Application\IntentRevisions\Actions\PublishIntent;
use App\Application\References\Actions\SaveReference;
use App\Domain\IntentRevisions\IntentFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Gate;
use Illuminate\Validation\ValidationException;

final class CatalogueController
{
    public function applications(Request $request, string $tenant): JsonResponse
    {
        $actor = $this->actor($request);
        $environment = $actor->scope['environment'];
        Gate::forUser($actor)->authorize('catalogue', ['application.read', $tenant, null, $environment]);
        $query = DB::table('app.catalogue_applications as a')->where('a.tenant_id', $tenant);
        if ($environment !== null) {
            $query->whereExists(fn ($q) => $q->selectRaw('1')->from('app.catalogue_deployments as d')->whereColumn('d.application_id', 'a.id')->whereColumn('d.tenant_id', 'a.tenant_id')->where('d.environment_id', $environment));
        }
        $after = $this->cursor($request, 'application', $tenant, $environment);
        if ($after !== null) {
            $query->where('a.id', '>', $after);
        }
        $rows = $query->orderBy('a.id')->limit(51)->get(['a.id', 'a.name', 'a.version']);
        $more = $rows->count() > 50;
        $rows = $rows->take(50);

        return response()->json(['applications' => $rows->map(fn ($row) => ['id' => $row->id, 'name' => $row->name, 'etag' => PublishIntent::etag($row->id, (int) $row->version)])->values(), 'next_cursor' => $more ? $this->encodeCursor('application', $tenant, $environment, $rows->last()->id ?? '') : null]);
    }

    public function show(Request $request, string $tenant, string $application): JsonResponse
    {
        $actor = $this->actor($request);
        Gate::forUser($actor)->authorize('catalogue', ['application.read', $tenant, $application, $actor->scope['environment']]);
        $row = $this->application($tenant, $application);
        $deployments = DB::table('app.catalogue_deployments')->where(['tenant_id' => $tenant, 'application_id' => $application]);
        if ($actor->scope['environment'] !== null) {
            $deployments->where('environment_id', $actor->scope['environment']);
        }
        $rows = $deployments->orderBy('id')->limit(101)->get(['id', 'environment_id', 'current_revision_id']);
        if ($rows->isEmpty()) {
            throw new IntentFailure('not_found', 404);
        }

        return response()->json(['id' => $row->id, 'name' => $row->name, 'etag' => PublishIntent::etag($row->id, (int) $row->version), 'deployments' => $rows])->header('ETag', PublishIntent::etag($row->id, (int) $row->version));
    }

    public function publish(Request $request, string $tenant, PublishIntent $publish, ?string $application = null): JsonResponse
    {
        if (strlen($request->getContent()) > 270336) {
            throw new IntentFailure('payload_too_large', 413);
        }
        $allowed = $application === null ? ['name', 'intent'] : ['intent'];
        if (array_diff(array_keys($request->all()), $allowed) !== []) {
            throw new IntentFailure('unknown_command_fields');
        }
        $input = $request->validate(['intent' => ['required', 'array'], ...($application === null ? ['name' => ['required', 'string', 'max:200']] : [])]);
        $response = $publish->handle($this->actor($request), $this->commandKey($request), $input['intent'], $application, $this->etag($request), $input['name'] ?? null);

        return response()->json($response, 201)->header('ETag', $response['etag'])->header('Location', '/v1/tenants/'.$tenant.'/applications/'.$response['application_id'].'/intent-revisions/'.$response['revision_id']);
    }

    public function revisions(Request $request, string $tenant, string $application): JsonResponse
    {
        $actor = $this->actor($request);
        Gate::forUser($actor)->authorize('catalogue', ['application.read', $tenant, $application, $actor->scope['environment']]);
        $this->application($tenant, $application);
        $q = DB::table('app.catalogue_revisions as r')->join('app.catalogue_deployments as d', function ($j): void {
            $j->on('r.tenant_id', '=', 'd.tenant_id')->on('r.deployment_id', '=', 'd.id');
        })->where('r.tenant_id', $tenant)->where('r.application_id', $application);
        if ($actor->scope['environment'] !== null) {
            $q->where('d.environment_id', $actor->scope['environment']);
        }
        $after = $this->cursor($request, 'revision:'.$application, $tenant, $actor->scope['environment']);
        if ($after !== null) {
            $q->where('r.sequence', '<', (int) $after);
        }
        $rows = $q->orderByDesc('r.sequence')->limit(51)->get(['r.id', 'r.deployment_id', 'r.sequence', 'r.parent_id', 'r.actor_id', 'r.digest', 'r.created_at']);
        $more = $rows->count() > 50;
        $rows = $rows->take(50);

        return response()->json(['revisions' => $rows, 'next_cursor' => $more ? $this->encodeCursor('revision:'.$application, $tenant, $actor->scope['environment'], (string) ($rows->last()->sequence ?? '')) : null]);
    }

    public function revision(Request $request, string $tenant, string $application, string $revision): JsonResponse
    {
        $actor = $this->actor($request);
        Gate::forUser($actor)->authorize('catalogue', ['application.read', $tenant, $application, $actor->scope['environment']]);
        $row = DB::table('app.catalogue_revisions as r')->join('app.catalogue_deployments as d', function ($j): void {
            $j->on('r.tenant_id', '=', 'd.tenant_id')->on('r.deployment_id', '=', 'd.id');
        })->where(['r.tenant_id' => $tenant, 'r.application_id' => $application, 'r.id' => $revision])->first(['r.*', 'd.environment_id']);
        if ($row === null || ($actor->scope['environment'] !== null && $row->environment_id !== $actor->scope['environment'])) {
            throw new IntentFailure('not_found', 404);
        }

        return response()->json(['id' => $row->id, 'application_id' => $application, 'deployment_id' => $row->deployment_id, 'sequence' => (int) $row->sequence, 'parent_id' => $row->parent_id, 'actor_id' => $row->actor_id, 'digest' => $row->digest, 'created_at' => $row->created_at, 'intent' => json_decode($row->canonical_intent, true, 512, JSON_THROW_ON_ERROR)]);
    }

    public function references(Request $request, string $tenant, string $kind): JsonResponse
    {
        $actor = $this->actor($request);
        Gate::forUser($actor)->authorize('catalogue', ['reference.read', $tenant, null, null]);
        $q = DB::table('app.catalogue_references as r')->join('app.catalogue_reference_versions as v', function ($j): void {
            $j->on('r.tenant_id', '=', 'v.tenant_id')->on('r.id', '=', 'v.reference_id')->on('r.version', '=', 'v.version');
        })->where(['r.tenant_id' => $tenant, 'r.kind' => $kind]);
        $after = $this->cursor($request, 'reference:'.$kind, $tenant, null);
        if ($after !== null) {
            $q->where('r.id', '>', $after);
        }
        $rows = $q->orderBy('r.id')->limit(51)->get(['r.id', 'r.kind', 'r.version', 'r.retired', 'v.definition']);
        $more = $rows->count() > 50;
        $rows = $rows->take(50);

        return response()->json(['references' => $rows->map(fn ($row) => ['id' => $row->id, 'kind' => $row->kind, 'version' => (int) $row->version, 'retired' => (bool) $row->retired, 'etag' => '"'.$row->id.':'.$row->version.'"', 'definition' => json_decode($row->definition, true, 512, JSON_THROW_ON_ERROR)])->values(), 'next_cursor' => $more ? $this->encodeCursor('reference:'.$kind, $tenant, null, $rows->last()->id ?? '') : null]);
    }

    public function referenceWrite(Request $request, string $tenant, string $kind, SaveReference $save, ?string $reference = null): JsonResponse
    {
        $result = $save->handle($this->actor($request), $kind, $this->commandKey($request), $request->all(), $reference, $this->etag($request), $request->route('retire') === 'yes');

        return response()->json($result, 201)->header('ETag', $result['etag']);
    }

    private function actor(Request $request): ActorContext
    {
        $actor = $request->attributes->get('verified_actor');
        if (! $actor instanceof ActorContext) {
            throw new IntentFailure('access_unavailable', 403);
        }

return $actor;
    }

    private function application(string $tenant, string $id): \stdClass
    {
        $row = DB::table('app.catalogue_applications')->where(['tenant_id' => $tenant, 'id' => $id])->first(['id', 'name', 'version']);
        if ($row === null) {
            throw new IntentFailure('not_found', 404);
        }

return $row;
    }

    private function commandKey(Request $request): string
    {
        $keys = $request->headers->all('idempotency-key');
        if (count($keys) !== 1 || ! is_string($keys[0]) || ! preg_match('/\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/', $keys[0])) {
            throw new IntentFailure('idempotency_key_required', 422, 'command_key');
        }

return $keys[0];
    }

    private function etag(Request $request): ?string
    {
        $values = $request->headers->all('if-match');
        if ($values === []) {
            return null;
        } if (count($values) !== 1 || ! is_string($values[0]) || ! preg_match('/\A"[0-9a-f-]{36}:[1-9][0-9]{0,15}"\z/', $values[0])) {
            throw new IntentFailure('invalid_precondition', 422, 'etag');
        }

return $values[0];
    }

    private function encodeCursor(string $kind, string $tenant, ?string $environment, string $value): string
    {
        return base64_encode(json_encode([$kind, $tenant, $environment, $value], JSON_THROW_ON_ERROR));
    }

    private function cursor(Request $request, string $kind, string $tenant, ?string $environment): ?string
    {
        $value = $request->query('cursor');
        if ($value === null) {
            return null;
        }
        $decoded = is_string($value) && strlen($value) <= 1024 ? base64_decode($value, true) : false;
        $data = $decoded !== false ? json_decode($decoded, true) : null;
        if (! is_array($data) || count($data) !== 4 || ($data[0] ?? null) !== $kind || ($data[1] ?? null) !== $tenant || ($data[2] ?? null) !== $environment || ! is_string($data[3] ?? null)
            || ! preg_match(str_starts_with($kind,'revision:') ? '/\A[1-9][0-9]{0,15}\z/' : '/\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/',$data[3])) {
            throw ValidationException::withMessages(['cursor' => 'Invalid page cursor.']);
        }

return $data[3];
    }
}
