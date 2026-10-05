<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

final class RequireConsoleHost
{
    /** @param Closure(Request): Response $next */
    public function handle(Request $request, Closure $next): Response
    {
        $url = config('app.url');
        $host = is_string($url) ? parse_url($url, PHP_URL_HOST) : null;
        if (! is_string($host) || ! hash_equals(strtolower($host), strtolower($request->getHost()))) {
            abort(400, 'Invalid console host.');
        }

        return $next($request);
    }
}
