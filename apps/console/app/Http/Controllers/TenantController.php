<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Tenancy\Contracts\TenantGateway;
use App\Domain\Identity\IdentityFailure;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

final class TenantController
{
    public function index(Request $request, TenantGateway $tenants): Response
    {
        $data = $tenants->read((string) $request->session()->get('identity.token'));
        Inertia::clearHistory();

        return Inertia::render('identity/Account', [
            'tenants' => $data['tenants'] ?? [],
            'canCreate' => ($data['installation_administrator'] ?? false) === true,
            'notice' => $request->session()->get('tenant_notice'),
        ]);
    }

    public function show(Request $request, string $tenant, TenantGateway $tenants): Response|RedirectResponse
    {
        try {
            $token = (string) $request->session()->get('identity.token');
            $data = $tenants->read($token, $tenant);
            $admin = ($data['membership']['role'] ?? null) === 'tenant_admin' && ($data['membership']['site_id'] ?? null) === null && ($data['membership']['environment'] ?? null) === null;
            $members = $admin ? $tenants->read($token, $tenant, 'memberships')['memberships'] : [];
            $quota = $admin ? $tenants->read($token, $tenant, 'quota') : null;
        } catch (IdentityFailure $error) {
            if (! in_array($error->status, [403, 404], true)) {
                throw $error;
            }

            return redirect('/account')->with('tenant_notice', 'This tenant is unavailable or your access has changed.');
        }
        Inertia::clearHistory();

        return Inertia::render('tenancy/Tenant', [
            'tenant' => $data['tenant'], 'membership' => $data['membership'], 'canAdminister' => $admin,
            'memberships' => $members, 'quota' => $quota, 'notice' => $request->session()->get('tenant_notice'),
        ]);
    }

    public function create(Request $request, TenantGateway $tenants): RedirectResponse
    {
        $input = $request->validate(['name' => ['required', 'string', 'max:200'], 'administrator_subject' => ['required', 'string', 'max:255'],
            'command_key' => ['required', 'uuid']]);
        unset($input['command_key']);
        try {
            $tenants->write((string) $request->session()->get('identity.token'), null, '', $request->string('command_key')->toString(), $input);
        } catch (IdentityFailure $error) {
            $this->formError($error);
        }

        return redirect('/account')->with('tenant_notice', 'Tenant created with its explicitly assigned administrator.');
    }

    public function update(Request $request, string $tenant, string $operation, TenantGateway $tenants): RedirectResponse
    {
        $request->validate(['command_key' => ['required', 'uuid']]);
        $fields = match ($operation) {
            'memberships' => ['revision', 'subject', 'role', 'state', 'site_id', 'environment', 'expires_at'],
            'quota' => ['revision', 'entitlement'], 'state' => ['revision', 'state'],
            default => throw new IdentityFailure(403),
        };
        try {
            $tenants->write((string) $request->session()->get('identity.token'), $tenant, $operation,
                $request->string('command_key')->toString(), $request->only($fields));
        } catch (IdentityFailure $error) {
            if (in_array($error->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your tenant access has changed.');
            }
            $this->formError($error);
        }

        return redirect($operation === 'state' ? '/account' : '/tenants/'.$tenant)->with('tenant_notice', 'Tenant settings saved.');
    }

    private function formError(IdentityFailure $error): never
    {
        if (in_array($error->status, [401, 503], true)) {
            throw $error;
        }
        throw ValidationException::withMessages(['settings' => match ($error->status) {
            409 => 'This record changed or the last administrator would be removed. Reload and review the current values.',
            403, 404 => 'You do not have permission for this tenant action.',
            default => 'Check the subject, scope, expiry and quota values.',
        }]);
    }
}
