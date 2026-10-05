<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Identity\Actions\ActivateOidcConnection;
use App\Application\Identity\Actions\BeginOidcLogin;
use App\Application\Identity\Actions\CompleteOidcLogin;
use App\Application\Identity\Actions\ResolveIdentitySession;
use App\Application\Identity\Actions\SaveOidcConnection;
use App\Application\Identity\Data\SessionCredentials;
use App\Domain\Identity\OidcConnection;
use App\Domain\Identity\OidcUrl;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

final class OidcController
{
    public function settings(Request $request, ResolveIdentitySession $resolve): JsonResponse
    {
        $resolve->handle((string) $request->header('X-Console-Session'), requireSetup: true);
        $installation = DB::table('app.oidc_installation')->where('id', 1)->first();
        $connection = OidcConnection::query()->where('revision', $installation?->latest_revision)->first();

        return response()->json([
            'settings' => $connection?->settings(), 'revision' => $installation->latest_revision ?? 0,
            'active_revision' => $installation?->active_revision,
        ]);
    }

    public function save(Request $request, SaveOidcConnection $save): JsonResponse
    {
        $settings = $request->validate([
            'revision' => ['required', 'integer', 'min:0'],
            'issuer' => ['required', 'string', 'max:2048'], 'client_id' => ['required', 'string', 'max:255'],
            'client_secret' => ['nullable', 'string', 'max:4096'], 'redirect_uri' => ['required', 'string', 'max:2048'],
            'administrator_subject' => ['required', 'string', 'max:255', 'regex:/\A[^\x00-\x1f\x7f]+\z/'],
            'private_networks' => ['present', 'array', 'max:16'],
            'private_networks.*' => ['string', 'regex:/\A(?:10\.(?:\d{1,3}\.){2}\d{1,3}\/(?:[89]|[12]\d|3[0-2])|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\/(?:1[2-9]|2\d|3[0-2])|192\.168\.\d{1,3}\.\d{1,3}\/(?:1[6-9]|2\d|3[0-2]))\z/'],
        ]);
        OidcUrl::origin($settings['issuer']);
        OidcUrl::origin($settings['redirect_uri'], callback: true);
        $settings['revision'] = (int) $settings['revision'];

        return response()->json(['settings' => $save->handle((string) $request->header('X-Console-Session'), $settings)], 201);
    }

    public function begin(Request $request, BeginOidcLogin $begin): JsonResponse
    {
        $request->validate(['purpose' => ['required', 'in:setup,login'], 'browser_binding' => ['required', 'regex:/\A[0-9a-f]{64}\z/']]);

        return response()->json($begin->handle($request->string('purpose')->toString(), $request->string('browser_binding')->toString(), (string) $request->header('X-Console-Session')));
    }

    public function callback(Request $request, CompleteOidcLogin $complete): JsonResponse
    {
        $request->validate([
            'state' => ['required', 'regex:/\A[0-9a-f]{64}\z/'], 'browser_binding' => ['required', 'regex:/\A[0-9a-f]{64}\z/'],
            'code' => ['required', 'string', 'max:4096'],
        ]);
        $result = $complete->handle($request->string('state')->toString(), $request->string('browser_binding')->toString(), $request->string('code')->toString(), (string) $request->header('X-Console-Session'));

        return response()->json($result instanceof SessionCredentials ? $this->session($result) : $result);
    }

    public function activate(Request $request, ActivateOidcConnection $activate): JsonResponse
    {
        $request->validate(['verification_token' => ['required', 'regex:/\A[0-9a-f]{64}\z/']]);

        return response()->json($this->session($activate->handle((string) $request->header('X-Console-Session'), $request->string('verification_token')->toString())));
    }

    /** @return array<string, mixed> */
    private function session(SessionCredentials $session): array
    {
        return ['session_token' => $session->token, 'expires_at' => $session->expiresAt, 'identity' => $session->identity->toArray()];
    }
}
