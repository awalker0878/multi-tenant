<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Application\Identity\Data\ConsoleActor;
use App\Domain\Catalogue\CatalogueFailure;
use App\Domain\Identity\IdentityFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;
use JsonException;

final class CatalogueWorkspaceController
{
    public function index(Request $request, string $tenant, CatalogueGateway $catalogue): Response
    {
        $token = $this->session($request);
        $environment = $this->environment($request);
        $data = $catalogue->call($token, $tenant, 'listApplications', environment: $environment, cursor: $this->cursor($request));
        Inertia::clearHistory();

        return Inertia::render('catalogue/Index', ['tenantId' => $tenant, 'environment' => $environment, 'applications' => $data['applications'], 'nextCursor' => $data['next_cursor'],
            'canCreate' => $catalogue->permitted($token, $tenant, 'application.write', environment: $environment), 'notice' => $request->session()->get('catalogue_notice')]);
    }

    public function editor(Request $request, string $tenant, CatalogueGateway $catalogue, ?string $application = null): Response
    {
        $token = $this->session($request);
        $environment = $this->environment($request);
        $data = null;
        $revision = null;
        if ($application !== null) {
            $data = $catalogue->call($token, $tenant, 'getApplication', ['application' => $application], environment: $environment);
            $revisionId = $request->query('revision') ?? $data['deployments'][0]['current_revision_id'];
            if (! is_string($revisionId)) {
                throw new CatalogueFailure(422, 'invalid_revision');
            }
            $revision = $catalogue->call($token, $tenant, 'getRevision', ['application' => $application, 'revision' => $revisionId], environment: $environment);
        }
        $refs = [];
        foreach (['environments' => 'listEnvironments', 'wsds' => 'listWsds', 'domains' => 'listSecurityDomains'] as $key => $op) {
            try {
                $refs[$key] = $catalogue->call($token, $tenant, $op);
            } catch (CatalogueFailure|IdentityFailure $e) {
                if ($e->status !== 403) {
                    throw $e;
                }$refs[$key] = ['references' => [], 'next_cursor' => null];
            }
        }
        $actor = $request->attributes->get('local_actor');
        Inertia::clearHistory();

        return Inertia::render('catalogue/Editor', ['tenantId' => $tenant, 'environment' => $environment, 'application' => $data, 'revision' => $revision, 'references' => $refs, 'actorId' => $actor instanceof ConsoleActor ? $actor->subject : null,
            'canWrite' => $catalogue->permitted($token, $tenant, 'application.write', $application, $revision['intent']['environment']['id'] ?? $environment)]);
    }

    public function save(Request $request, string $tenant, CatalogueGateway $catalogue, ?string $application = null): RedirectResponse
    {
        $request->validate(['command_key' => ['required', 'uuid', 'lowercase'], 'etag' => ['nullable', 'string', 'max:100'], 'name' => ['required_without:application', 'nullable', 'string', 'max:200'], 'intent_json' => ['required', 'string', 'max:262144']]);
        try {
            $intent = json_decode($request->string('intent_json')->toString(), true, 64, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            throw ValidationException::withMessages(['intent_json' => 'Import a valid JSON intent document.']);
        }
        if (! is_array($intent)) {
            throw ValidationException::withMessages(['intent_json' => 'Import an object containing the complete application intent.']);
        }
        try {
            $result = $catalogue->call($this->session($request), $tenant, $application === null ? 'createApplication' : 'publishRevision', $application === null ? [] : ['application' => $application],
                ['intent' => $intent, ...($application === null ? ['name' => $request->string('name')->toString()] : [])], $request->string('command_key')->toString(), $application === null ? null : $request->input('etag'));
        } catch (CatalogueFailure|IdentityFailure $e) {
            if (in_array($e->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your application access has changed.');
            }
            $message = match ($e->status) {
                412 => 'This application changed. Compare your draft with the latest revision before saving.',409 => 'This command conflicts with existing intent. Review the result and use a new command only for a changed request.',503 => 'The outcome is not confirmed. Keep this draft unchanged and retry the same command.',default => 'Check '.($e instanceof CatalogueFailure ? $e->field.': '.str_replace('_', ' ', $e->reason) : 'the submitted values').'.'
            };
            throw ValidationException::withMessages(['intent_json' => $message, 'catalogue_status' => (string) $e->status]);
        }

        return redirect('/tenants/'.$tenant.'/applications/'.$result['application_id'].'?environment='.urlencode($intent['environment']['id']))->with('catalogue_notice', 'Published revision '.$result['sequence'].'.');
    }

    public function show(Request $request, string $tenant, string $application, CatalogueGateway $catalogue): Response
    {
        $token = $this->session($request);
        $environment = $this->environment($request);
        $args = ['application' => $application];
        $data = $catalogue->call($token, $tenant, 'getApplication', $args, environment: $environment);
        $history = $catalogue->call($token, $tenant, 'listRevisions', $args, environment: $environment, cursor: $this->cursor($request));
        $id = $request->query('revision') ?? $data['deployments'][0]['current_revision_id'];
        if (! is_string($id)) {
            throw new CatalogueFailure(422, 'invalid_revision');
        }
        $revision = $catalogue->call($token, $tenant, 'getRevision', $args + ['revision' => $id], environment: $environment);
        $compare = null;
        if (is_string($request->query('compare'))) {
            $compare = $catalogue->call($token, $tenant, 'getRevision', $args + ['revision' => $request->query('compare')], environment: $environment);
        }
        Inertia::clearHistory();

        return Inertia::render('catalogue/Application', ['tenantId' => $tenant, 'environment' => $environment, 'application' => $data, 'history' => $history, 'revision' => $revision, 'comparison' => $compare,
            'canWrite' => $catalogue->permitted($token, $tenant, 'application.write', $application, $revision['intent']['environment']['id']), 'notice' => $request->session()->get('catalogue_notice')]);
    }

    public function status(Request $request, string $tenant, string $application, CatalogueGateway $catalogue): JsonResponse
    {
        try {
            $data = $catalogue->call($this->session($request), $tenant, 'getApplication', ['application' => $application], environment: $this->environment($request));

            return response()->json(['etag' => $data['etag']]);
        } catch (CatalogueFailure|IdentityFailure $e) {
            return response()->json(['error' => 'access_unavailable'], in_array($e->status, [401, 403, 404], true) ? 403 : 503);
        }
    }

    public function references(Request $request, string $tenant, CatalogueGateway $catalogue): Response
    {
        $kind = $request->query('kind', 'Environment');
        if (! in_array($kind, ['Environment', 'Wsd', 'SecurityDomain'], true)) {
            throw new CatalogueFailure(422, 'invalid_reference_kind');
        }
        $data = $catalogue->call($this->session($request), $tenant, 'list'.$kind.'s', cursor: $this->cursor($request));
        Inertia::clearHistory();

        return Inertia::render('catalogue/References', ['tenantId' => $tenant, 'kind' => $kind, 'page' => $data, 'canWrite' => $catalogue->permitted($this->session($request), $tenant, 'reference.write'), 'notice' => $request->session()->get('catalogue_notice'), 'actorId' => $request->attributes->get('local_actor') instanceof ConsoleActor ? $request->attributes->get('local_actor')->subject : '']);
    }

    public function referenceSave(Request $request, string $tenant, CatalogueGateway $catalogue): RedirectResponse
    {
        $v = $request->validate(['kind' => ['required', 'in:Environment,Wsd,SecurityDomain'], 'command_key' => ['required', 'uuid'], 'reference' => ['nullable', 'uuid'], 'etag' => ['nullable', 'string', 'max:100'], 'retire' => ['boolean'], 'name' => ['required_unless:retire,true', 'string', 'max:200'], 'owner_id' => ['required_unless:retire,true', 'uuid'], 'shareable' => ['boolean'], 'zone' => ['nullable', 'in:PAZ,OZ,RZ,HRZ']]);
        $retire = ($v['retire'] ?? false) === true;
        $id = $v['reference'] ?? null;
        $operation = ($retire ? 'retire' : ($id === null ? 'create' : 'update')).$v['kind'];
        $body = $retire ? [] : ['name' => $v['name'], 'owner_id' => $v['owner_id'], ...($v['kind'] === 'Environment' ? [] : ['shareable' => $v['shareable'] ?? false]), ...($v['kind'] === 'SecurityDomain' ? ['zone' => $v['zone'] ?? null] : [])];
        try {
            $catalogue->call($this->session($request), $tenant, $operation, $id === null ? [] : ['reference' => $id], $body, $v['command_key'], $v['etag'] ?? null);
        } catch (CatalogueFailure|IdentityFailure $e) {
            throw ValidationException::withMessages(['name' => match ($e->status) {
                409 => 'This reference is in use, retired, or its identity cannot change.',412 => 'This reference changed. Reload before editing.',503 => 'Outcome not confirmed. Retry the same unchanged command.',default => 'Check reference values and active owner membership.'
            }]);
        }

        return redirect('/tenants/'.$tenant.'/catalogue-references?kind='.$v['kind'])->with('catalogue_notice', 'Reference saved.');
    }

    private function session(Request $request): string
    {
        return (string) $request->session()->get('identity.token');
    }

    private function cursor(Request $request): ?string
    {
        $value = $request->query('cursor');
        if ($value !== null && (! is_string($value) || strlen($value) > 1024)) {
            throw new CatalogueFailure(422, 'invalid_cursor');
        }

        return $value;
    }

    private function environment(Request $request): ?string
    {
        $v = $request->query('environment');
        if ($v !== null && (! is_string($v) || ! preg_match('/\A[0-9a-f-]{36}\z/', $v))) {
            throw new CatalogueFailure(422, 'invalid_environment');
        }

        return $v;
    }
}
