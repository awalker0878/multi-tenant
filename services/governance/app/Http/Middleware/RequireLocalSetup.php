<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use App\Application\Identity\Actions\ResolveLocalSession;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

final class RequireLocalSetup
{
    public function __construct(private readonly ResolveLocalSession $resolve) {}

    /** @param Closure(Request): Response $next */
    public function handle(Request $request, Closure $next): Response
    {
        $identity = $this->resolve->handle((string) $request->header('X-Console-Session'), requireSetup: true);
        $request->attributes->set('local_identity', $identity);

        return $next($request);
    }
}
