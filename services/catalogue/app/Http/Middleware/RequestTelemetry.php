<?php

declare(strict_types=1);

namespace App\Http\Middleware;

use App\Application\Foundation\Contracts\SignalBuffer;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;
use Throwable;

final class RequestTelemetry
{
    public function __construct(private readonly SignalBuffer $buffer) {}

    /**
     * @param Closure(Request): Response $next */
    public function handle(Request $request, Closure $next): Response
    {
        $incoming = $request->headers->all('traceparent');
        $valid = count($incoming) === 1 && is_string($incoming[0]) && preg_match('/\A00-([0-9a-f]{32})-([0-9a-f]{16})-0[01]\z/', $incoming[0], $matches)
            && $matches[1] !== str_repeat('0', 32) && $matches[2] !== str_repeat('0', 16);
        $trace = $valid ? $matches[1] : bin2hex(random_bytes(16));
        $parent = $valid ? $matches[2] : null;
        $span = bin2hex(random_bytes(8));
        $started = hrtime(true);
        $timestamp = (int) (microtime(true) * 1000000);
        try {
            $response = $next($request);
        } catch (Throwable $error) {
            $this->record($request, 500, $trace, $span, $parent, $started, $timestamp);
            throw $error;
        }
        $state = $this->record($request, $response->getStatusCode(), $trace, $span, $parent, $started, $timestamp);
        $response->headers->set('X-Trace-Id', $trace);
        $response->headers->set('X-Span-Id', $span);
        $response->headers->set('X-Telemetry-State', $state);

        return $response;
    }

    private function record(Request $request, int $status, string $trace, string $span, ?string $parent, int $started, int $timestamp): string
    {
        if (config('telemetry.enabled') !== true) {
            return 'disabled';
        }
        $revision = config('telemetry.source_revision');
        $environment = config('telemetry.environment');
        if (! is_string($revision) || ! preg_match('/\A[0-9a-f]{40}\z/', $revision)
            || ! in_array($environment, ['development', 'p01-compose', 'p01-kubernetes'], true)) {
            return 'unavailable';
        }
        $path = $request->getPathInfo();
        $method = $request->getMethod();

        return $this->buffer->append([
            'schema_version' => 1, 'event' => 'http.response', 'service' => 'catalogue',
            'source_revision' => $revision, 'environment' => $environment,
            'timestamp_unix_us' => $timestamp, 'trace_id' => $trace, 'span_id' => $span,
            'parent_span_id' => $parent,
            'route' => in_array($path, ['/', '/health/live', '/health/ready', '/health/dependencies'], true) ? $path : 'other',
            'method' => in_array($method, ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'], true) ? $method : 'OTHER',
            'status' => $status, 'duration_us' => (int) ((hrtime(true) - $started) / 1000),
        ]);
    }
}
