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

final class LocalIdentityController
{
    public function login(Request $request, LoginLocalAdministrator $login): JsonResponse
    {
        $request->validate(['username' => ['required', 'string', 'max:128'], 'password' => ['required', 'string', 'max:512']]);

        return $this->sessionResponse($login->handle($request->string('username')->toString(), $request->string('password')->toString()));
    }

    public function password(Request $request, ChangeLocalPassword $change): JsonResponse
    {
        $request->validate([
            'current_password' => ['required', 'string', 'max:512'],
            'password' => ['required', 'string', 'min:15', 'max:128', 'confirmed'],
        ]);

        return $this->sessionResponse($change->handle((string) $request->header('X-Console-Session'), $request->string('current_password')->toString(), $request->string('password')->toString()));
    }

    public function session(Request $request, ResolveIdentitySession $resolve): JsonResponse
    {
        return response()->json(['identity' => $resolve->handle((string) $request->header('X-Console-Session'))->toArray()]);
    }

    public function logout(Request $request, LogoutIdentitySession $logout): JsonResponse
    {
        $logout->handle((string) $request->header('X-Console-Session'));

        return response()->json(['status' => 'signed_out']);
    }

    public function setup(Request $request): JsonResponse
    {
        return response()->json(['identity' => $request->attributes->get('local_identity')->toArray(), 'oidc' => ['state' => 'not_configured']]);
    }

    private function sessionResponse(SessionCredentials $session): JsonResponse
    {
        return response()->json(['session_token' => $session->token, 'expires_at' => $session->expiresAt, 'identity' => $session->identity->toArray()]);
    }
}
