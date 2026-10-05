<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use App\Application\Identity\Contracts\IdentityGateway;
use App\Domain\Identity\IdentityFailure;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

final class RequireLocalIdentity
{
    public function __construct(private readonly IdentityGateway $identity) {}

    /** @param Closure(Request): Response $next */
    public function handle(Request $request, Closure $next): Response
    {
        $token = $request->session()->get('identity.token');
        if (! is_string($token)) {
            return redirect('/login');
        }
        try {
            $actor = $this->identity->current($token);
        } catch (IdentityFailure $error) {
            if ($error->status !== 401) {
                throw $error;
            }
            $request->session()->invalidate();
            $request->session()->regenerateToken();

            return redirect('/login');
        }
        if ($actor->passwordChangeRequired && ! $request->routeIs('identity.password', 'identity.password.update', 'identity.logout')) {
            return redirect('/password');
        }
        $request->attributes->set('local_actor', $actor);

        return $next($request);
    }
}
