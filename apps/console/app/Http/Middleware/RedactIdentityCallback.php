<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

final class RedactIdentityCallback
{
    /** @param Closure(Request): Response $next */
    public function handle(Request $request, Closure $next): Response
    {
        if ($request->getPathInfo() !== '/identity/callback') {
            return $next($request);
        }
        try {
            $response = $next($request);
            $response->headers->set('Referrer-Policy', 'no-referrer');

            return $response;
        } finally {
            // StartSession records the current URL after inner middleware returns.
            // Never persist a one-use provider code/state in Laravel's previous URL.
            $request->query->replace([]);
            $request->server->set('QUERY_STRING', '');
            $request->server->set('REQUEST_URI', '/identity/callback');
        }
    }
}
