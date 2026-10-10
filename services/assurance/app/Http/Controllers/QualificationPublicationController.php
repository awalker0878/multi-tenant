<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Foundation\Contracts\SecretReader;
use App\Application\Qualification\Actions\QualificationAuthorityLedger;
use App\Application\Qualification\Actions\ResolveQualification;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Throwable;

/**
 * Service-only Assurance authority boundary. Reviewer and observer credentials
 * cannot be substituted for each other or borrowed from Planning callers.
 */
final class QualificationPublicationController
{
    public function __invoke(
        Request $request,
        string $tenant,
        SecretReader $secrets,
        QualificationAuthorityLedger $ledger,
        ResolveQualification $resolver
    ): JsonResponse {
        abort_unless(config('planning.qualification_authority_mode') === 'database', 503,
            'qualification_publication_not_commissioned');
        abort_if(strlen($request->getContent()) > 524288, 413);
        $input = $request->validate([
            'operation' => ['required', 'in:publish,suspend,revoke,restore'],
            'command_id' => ['required', 'uuid'],
            'expected_epoch' => ['required', 'integer', 'min:0'],
            'reason' => ['required', 'string', 'max:1024'],
            'qualification_scope' => [
                'required',
                'array:tenant_id,site_id,endpoint_id,native_scope,installed_tuple,action,method,profile_digest,artifacts',
            ],
            'qualification_scope.tenant_id' => ['required', 'uuid'],
            'qualification_scope.site_id' => ['required', 'uuid'],
            'qualification_scope.endpoint_id' => ['required', 'uuid'],
            'qualification_scope.native_scope' => ['required', 'string', 'max:1024'],
            'qualification_scope.installed_tuple' => ['required', 'array'],
            'qualification_scope.action' => ['required', 'string'],
            'qualification_scope.method' => ['required', 'string'],
            'qualification_scope.profile_digest' => ['required', 'regex:/^[a-f0-9]{64}$/'],
            'qualification_scope.artifacts' => ['required', 'array'],
            'bundle' => ['required_if:operation,publish,restore', 'nullable', 'array'],
        ]);
        abort_unless($input['qualification_scope']['tenant_id'] === $tenant
            && count(array_diff(array_keys($request->all()), [
                'operation', 'command_id', 'expected_epoch', 'reason', 'qualification_scope', 'bundle',
            ])) === 0, 403);

        $reviewer = $secrets->read(config('planning.qualification_reviewer_credential_file'));
        $observer = $secrets->read(config('planning.qualification_observer_credential_file'));
        $planning = $secrets->read(config('planning.credential_file'));
        abort_if(! is_string($reviewer) || $reviewer === ''
            || ! is_string($observer) || $observer === '' || $reviewer === $observer
            || $planning === $reviewer || $planning === $observer, 503,
            'distinct_publication_authorities_required');
        $operation = $input['operation'];
        $requiredCredential = $operation === 'suspend' ? $observer : $reviewer;
        $authorization = $request->headers->all('authorization');
        abort_unless(count($authorization) === 1
            && hash_equals('Bearer '.$requiredCredential, (string) $authorization[0]), 403);

        $scope = $input['qualification_scope'];
        $bundle = $input['bundle'] ?? null;
        $decisionSha = '';
        $decisionRevision = 0;
        $reviewerId = $operation === 'suspend' ? 'assurance-native-observer' : 'assurance-publication-reviewer';
        if ($operation === 'publish' || $operation === 'restore') {
            abort_unless(is_array($bundle), 422);
            try {
                $qualification = $resolver->verifyProposed($bundle, $scope);
                abort_unless($qualification['status'] === 'qualified'
                    && in_array($qualification['evidence_level'], ['E3', 'E4'], true), 423,
                    'native_qualification_unverified');
                $decisionSha = $qualification['verification']['decision_sha256'];
                $envelope = base64_decode($bundle['decision']['content_base64'] ?? '', true);
                abort_unless(is_string($envelope), 423, 'signed_decision_missing');
                $signed = json_decode($envelope, true, 64, JSON_THROW_ON_ERROR);
                abort_unless(is_array($signed) && is_int($signed['revision'] ?? null)
                    && is_string($signed['subject_id'] ?? null), 423, 'reviewed_decision_invalid');
                $decisionRevision = $signed['revision'];
                $reviewerId = $signed['subject_id'];
                // Runtime is independently sourced at every read. Never persist a
                // requester-supplied or temporarily-attached runtime assertion.
                unset($bundle['runtime']);
            } catch (Throwable) {
                abort(423, 'signed_native_publication_unverified');
            }
        } else {
            abort_unless($bundle === null, 422, 'mutation_bundle_not_allowed');
        }

        $result = $ledger->mutate(
            $scope, $operation, $input['command_id'], (int) $input['expected_epoch'],
            $input['reason'], $bundle, $decisionSha, $decisionRevision, $reviewerId
        );

        return response()->json([
            'scope_sha256' => \App\Domain\Qualification\NativeQualification::digest($scope),
            'state' => $result['state'],
            'authority_epoch' => $result['authority_epoch'],
            'decision_sha256' => $result['decision_sha256'],
            'decision_revision' => $result['decision_revision'],
        ])->header('Cache-Control', 'no-store, private');
    }
}
