<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use App\Application\Identity\Contracts\ServiceCredentials;
use App\Domain\Identity\IdentityDenied;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

final class AuthenticateService
{
    public function __construct(private readonly ServiceCredentials $credentials) {}

    /** @param Closure(Request): Response $next */
    public function handle(Request $request, Closure $next): Response
    {
        $authorization = $request->headers->all('authorization');
        if (count($authorization) !== 1 || ! is_string($authorization[0])
            || ! preg_match('/\ABearer ([A-Za-z0-9_-]{32,4096})\z/', $authorization[0], $matches)) {
            throw new IdentityDenied('invalid_workload_identity');
        }
        $request->attributes->set('verified_service', $this->credentials->authenticate($matches[1]));
        $response = $next($request);
        $response->headers->set('Cache-Control', 'no-store, private');

        return $response;
    }
}
