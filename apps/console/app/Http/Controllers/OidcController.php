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
use Symfony\Component\HttpFoundation\Response as HttpResponse;

final class OidcController
{
    public function settings(Request $request, IdentityGateway $identity): Response
    {
        $data = $identity->settings((string) $request->session()->get('identity.token'));
        // The owner returns an explicit settings projection. Never forward arbitrary upstream data.
        $settings = is_array($data['settings'] ?? null) ? array_intersect_key($data['settings'], array_flip([
            'issuer', 'client_id', 'administrator_subject', 'private_networks', 'secret_configured',
        ])) : null;

        return Inertia::render('identity/Setup', [
            'settings' => $settings, 'revision' => $data['revision'] ?? 0, 'activeRevision' => $data['active_revision'] ?? null,
            'callbackUrl' => rtrim((string) config('app.url'), '/').'/identity/callback',
            'verified' => $request->session()->get('oidc.proof_revision') === ($data['revision'] ?? null),
            'notice' => $request->session()->get('oidc_notice'),
            'federated' => $request->attributes->get('local_actor')->federated,
        ]);
    }

    public function save(Request $request, IdentityGateway $identity): RedirectResponse
    {
        $settings = $request->validate([
            'revision' => ['required', 'integer', 'min:0'], 'issuer' => ['required', 'string', 'max:2048'],
            'client_id' => ['required', 'string', 'max:255'], 'client_secret' => ['nullable', 'string', 'max:4096'],
            'administrator_subject' => ['required', 'string', 'max:255'],
            'private_networks' => ['present', 'array', 'max:16'], 'private_networks.*' => ['string', 'max:32'],
        ]);
        $settings['redirect_uri'] = rtrim((string) config('app.url'), '/').'/identity/callback';
        try {
            $identity->saveSettings((string) $request->session()->get('identity.token'), $settings);
        } catch (IdentityFailure $error) {
            $this->setupError($error);
        }
        $request->session()->forget('oidc');

        return redirect('/setup')->with('oidc_notice', 'Settings saved. Test administrator sign-in before activation.');
    }

    public function test(Request $request, IdentityGateway $identity): HttpResponse
    {
        return $this->begin($request, $identity, 'setup');
    }

    public function login(Request $request, IdentityGateway $identity): HttpResponse
    {
        return $this->begin($request, $identity, 'login');
    }

    private function begin(Request $request, IdentityGateway $identity, string $purpose): HttpResponse
    {
        $binding = bin2hex(random_bytes(32));
        try {
            $url = $identity->begin($purpose, $binding, (string) $request->session()->get('identity.token'));
        } catch (IdentityFailure $error) {
            if ($purpose === 'setup') {
                $this->setupError($error);
            }

            return redirect('/login')->withErrors(['password' => 'Single sign-on is not available. Contact your administrator or try again.']);
        }
        $request->session()->forget('oidc');
        $request->session()->put('oidc.binding', $binding);
        $request->session()->put('oidc.purpose', $purpose);

        return Inertia::location($url);
    }

    public function callback(Request $request, IdentityGateway $identity): RedirectResponse
    {
        $binding = $request->session()->pull('oidc.binding');
        $purpose = $request->session()->pull('oidc.purpose');
        $target = $purpose === 'setup' ? '/setup' : '/login';
        $state = $request->query('state');
        $code = $request->query('code');
        if (! is_string($binding) || ! is_string($state) || ! preg_match('/\A[0-9a-f]{64}\z/', $state)
            || ! is_string($code) || $code === '' || strlen($code) > 4096 || $request->has('error')) {
            return redirect($target)->with('oidc_notice', 'Sign-in was not verified. Start a new sign-in attempt.');
        }
        try {
            $result = $identity->callback($state, $binding, $code, (string) $request->session()->get('identity.token'));
        } catch (IdentityFailure) {
            return redirect($target)->with('oidc_notice', 'Sign-in was not verified. Check the provider settings and try again.');
        }
        if ($result instanceof ConsoleSession) {
            return $this->accept($request, $result);
        }
        $request->session()->put('oidc.proof', $result['verification_token']);
        $request->session()->put('oidc.proof_revision', $result['revision']);

        return redirect('/setup')->with('oidc_notice', 'Federated administrator verified. You can now activate single sign-on.');
    }

    public function activate(Request $request, IdentityGateway $identity): RedirectResponse
    {
        $proof = $request->session()->get('oidc.proof');
        if (! is_string($proof)) {
            throw ValidationException::withMessages(['settings' => 'Test administrator sign-in first.']);
        }
        try {
            $session = $identity->activate((string) $request->session()->get('identity.token'), $proof);
        } catch (IdentityFailure $error) {
            $request->session()->forget('oidc');
            $this->setupError($error);
        }

        return $this->accept($request, $session);
    }

    private function accept(Request $request, ConsoleSession $session): RedirectResponse
    {
        $request->session()->invalidate();
        $request->session()->regenerateToken();
        $request->session()->put('identity.token', $session->token);

        return redirect($session->actor->installationAdministrator ? '/setup' : '/account');
    }

    private function setupError(IdentityFailure $error): never
    {
        if ($error->status === 401 || $error->status === 403) {
            throw $error;
        }
        $message = match ($error->status) {
            409 => 'The settings or verification changed. Reload this page and test sign-in again.',
            422 => 'Check the issuer, client registration, administrator subject and permitted network ranges.',
            default => 'The identity provider could not be reached or verified. Your existing access remains available.',
        };
        throw ValidationException::withMessages(['settings' => $message]);
    }
}
