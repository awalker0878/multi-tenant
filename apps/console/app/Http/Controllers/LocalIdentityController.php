<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Identity\Contracts\IdentityGateway;
use App\Application\Identity\Data\ConsoleSession;
use App\Domain\Identity\IdentityFailure;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

final class LocalIdentityController
{
    public function login(): Response
    {
        return Inertia::render('identity/Login');
    }

    public function authenticate(Request $request, IdentityGateway $identity): RedirectResponse
    {
        $request->validate(['username' => ['required', 'string', 'max:128'], 'password' => ['required', 'string', 'max:512']]);
        if (is_string($request->session()->get('identity.token'))) {
            return redirect('/setup');
        }
        try {
            $session = $identity->login($request->string('username')->toString(), $request->string('password')->toString());
        } catch (IdentityFailure $error) {
            $this->credentialError($error);
        }

        return $this->acceptSession($request, $session);
    }

    public function password(): Response
    {
        return Inertia::render('identity/Password');
    }

    public function updatePassword(Request $request, IdentityGateway $identity): RedirectResponse
    {
        $request->validate(['current_password' => ['required', 'string', 'max:512'], 'password' => ['required', 'string', 'min:15', 'max:128', 'confirmed']]);
        try {
            $session = $identity->changePassword((string) $request->session()->get('identity.token'), $request->string('current_password')->toString(), $request->string('password')->toString());
        } catch (IdentityFailure $error) {
            $this->credentialError($error);
        }

        return $this->acceptSession($request, $session);
    }

    public function logout(Request $request, IdentityGateway $identity): RedirectResponse
    {
        $identity->logout((string) $request->session()->get('identity.token'));
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect('/login');
    }

    private function acceptSession(Request $request, ConsoleSession $session): RedirectResponse
    {
        $request->session()->invalidate();
        $request->session()->regenerateToken();
        $request->session()->put('identity.token', $session->token);

        return redirect($session->actor->passwordChangeRequired ? '/password' : '/setup');
    }

    private function credentialError(IdentityFailure $error): never
    {
        if ($error->status === 503 || $error->status === 403) {
            throw $error;
        }
        $message = match ($error->status) {
            429 => 'Too many attempts. Wait one minute before trying again.',
            422 => 'Choose a different password with at least 15 characters.',
            default => 'The account or password could not be verified.',
        };
        throw ValidationException::withMessages(['password' => $message]);
    }
}
