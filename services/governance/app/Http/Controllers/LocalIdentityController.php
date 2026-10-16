<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Identity\Actions\ChangeLocalPassword;
use App\Application\Identity\Actions\LoginLocalAdministrator;
use App\Application\Identity\Actions\LogoutIdentitySession;
use App\Application\Identity\Actions\ResolveIdentitySession;
use App\Application\Identity\Data\SessionCredentials;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

final class LocalIdentityController
{
    public function login(Request $request, LoginLocalAdministrator $login): JsonResponse
    {
        $this->fields($request, ['username', 'password']);
        $request->validate(['username' => ['required', 'string', 'max:128'], 'password' => ['required', 'string', 'max:512']]);

        return $this->sessionResponse($login->handle($request->string('username')->toString(), $request->string('password')->toString(), $this->key($request), $this->workload($request)));
    }

    public function password(Request $request, ChangeLocalPassword $change): JsonResponse
    {
        $this->fields($request, ['current_password', 'password', 'password_confirmation']);
        $request->validate([
            'current_password' => ['required', 'string', 'max:512'],
            'password' => ['required', 'string', 'min:15', 'max:128', 'confirmed'],
        ]);

        return $this->sessionResponse($change->handle((string) $request->header('X-Console-Session'), $request->string('current_password')->toString(), $request->string('password')->toString(), $this->key($request), $this->workload($request)));
    }

    public function session(Request $request, ResolveIdentitySession $resolve): JsonResponse
    {
        return response()->json(['identity' => $resolve->handle((string) $request->header('X-Console-Session'))->toArray()]);
    }

    public function logout(Request $request, LogoutIdentitySession $logout): JsonResponse
    {
        $this->fields($request, []);
        $logout->handle((string) $request->header('X-Console-Session'), $this->key($request), $this->workload($request));

        return response()->json(['status' => 'signed_out']);
    }

    public function setup(Request $request): JsonResponse
    {
        return response()->json(['identity' => $request->attributes->get('local_identity')->toArray(),
            'oidc' => ['state' => DB::table('app.oidc_installation')->where('id', 1)->value('active_revision') === null ? 'not_configured' : 'active']]);
    }

    /** @param list<string> $allowed */
    private function fields(Request $request, array $allowed): void
    {
        if (array_diff(array_keys($request->all()), $allowed) !== []) {
            throw ValidationException::withMessages(['request' => 'Unexpected identity fields.']);
        }
    }

    private function key(Request $request): string
    {
        $keys = $request->headers->all('idempotency-key');
        if (count($keys) !== 1 || ! is_string($keys[0]) || ! preg_match('/\A[a-f0-9]{32,64}\z/', $keys[0])) {
            throw ValidationException::withMessages(['idempotency_key' => 'Supply one strong command key.']);
        }

        return $keys[0];
    }

    private function workload(Request $request): string
    {
        // AuthenticateConsole has already verified this exact, unique credential.
        return substr((string) $request->header('Authorization'), 7);
    }

    private function sessionResponse(SessionCredentials $session): JsonResponse
    {
        return response()->json(['session_token' => $session->token, 'expires_at' => $session->expiresAt, 'identity' => $session->identity->toArray()]);
    }
}
