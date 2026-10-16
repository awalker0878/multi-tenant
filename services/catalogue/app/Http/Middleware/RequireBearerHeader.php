<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * Reject malformed and absent service credentials BEFORE transport
 * deserialization, secret mounting, and any tenant-scoped database read.
 * The existing bounded-context authority still validates the bearer secret;
 * passing this presence gate never grants an identity or an action.
 */
final class RequireBearerHeader
{
    /** @param Closure(Request): Response $next */
    public function handle(Request $request, Closure $next): Response
    {
        $values = $request->headers->all('authorization');
        if (count($values) !== 1 || ! is_string($values[0])
            || ! preg_match('/\ABearer [A-Za-z0-9_-]{32,4096}\z/D', $values[0])) {
            return response()->json(['error' => 'invalid_workload_identity'], 401, [
                'WWW-Authenticate' => 'Bearer',
                'Cache-Control' => 'no-store, private',
            ]);
        }

        return $next($request);
    }
}
