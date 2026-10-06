<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use App\Application\Authorization\Contracts\ConsoleCaller;
use App\Application\Authorization\Contracts\DelegatedAuthority;
use App\Domain\Authorization\AccessDenied;
use App\Domain\IntentRevisions\IntentFailure;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

final class RequireDelegatedActor
{
    public function __construct(private readonly DelegatedAuthority $authority, private readonly ConsoleCaller $caller) {}

    /**
     * @param Closure(Request): Response $next */
    public function handle(Request $request, Closure $next, string $action): Response
    {
        if (strlen($request->getContent()) > 270336) {
            throw new IntentFailure('payload_too_large', 413);
        }
        $workload = $request->headers->all('authorization');
        if (count($workload) !== 1 || ! is_string($workload[0])
            || ! preg_match('/\ABearer ([A-Za-z0-9_-]{32,4096})\z/', $workload[0], $matches) || ! $this->caller->accepts($matches[1])) {
            throw new AccessDenied(401);
        }
        // Both the calling workload and the delegated actor are required.
        $headers = $request->headers->all('x-actor-delegation');
        $tenant = $request->route('tenant');
        if (count($headers) !== 1 || ! is_string($headers[0]) || ! is_string($tenant)) {
            throw new AccessDenied;
        }
        $scope = [];
        foreach (['site_id' => 'site', 'environment' => 'environment', 'resource_id' => 'application'] as $field => $parameter) {
            $value = $request->route($parameter);
            if ($field === 'environment' && $value === null) {
                $value = $request->isMethod('GET') ? $request->query('environment') : $request->input('intent.environment.id');
            }
            if ($value !== null && ! is_string($value)) {
                throw new AccessDenied;
            }
            $scope[$field] = $value;
        }
        $actor = $this->authority->check($headers[0], $tenant, $action, $scope);
        $request->attributes->set('verified_actor', $actor);
        try {
            $response = $next($request);
            $response->headers->set('Cache-Control', 'no-store, private');

            return $response;
        } finally {
            $request->attributes->remove('verified_actor');
        }
    }
}
