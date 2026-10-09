<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use App\Application\Inventory\Contracts\InventoryGateway;
use App\Application\Catalogue\Contracts\CatalogueGateway;
use App\Domain\Inventory\InventoryFailure;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Inertia\Response;

final class MigrationReviewController
{
    public function show(Request $request, string $tenant, string $site, InventoryGateway $inventory, ?string $profile = null): Response
    {
        $workspace = $inventory->call($this->session($request), $tenant, ($profile === null ? 'getMigrationReview' : 'getVmMigrationReview'), ['site' => $site, ...($profile === null ? [] : ['profile' => $profile])]);
        Inertia::clearHistory();

        return Inertia::render('inventory/Migration', ['tenantId' => $tenant, 'siteId' => $site, 'profileId' => $profile, 'workspace' => $workspace, 'notice' => $request->session()->get('inventory_notice')]);
    }

    public function catalogueOptions(
        Request $request, string $tenant, string $site, CatalogueGateway $catalogue
    ): JsonResponse {
        // No arbitrary revision, digest, workload name or native identity
        // enters this response. Fetch the CURRENT revision through Catalogue's
        // own authenticated, scope-authorized gateway.
        $token = $this->session($request);
        $query = $request->validate([
            'application' => ['sometimes', 'uuid', 'lowercase'],
            'environment' => ['sometimes', 'uuid', 'lowercase'],
        ]);
        $data = $catalogue->call($token, $tenant, 'listApplications');
        $out = ['applications' => $data['applications'] ?? [], 'current' => null];
        if (isset($query['application'])) {
            $application = $catalogue->call($token, $tenant, 'getApplication',
                ['application' => $query['application']], environment: $query['environment'] ?? null);
            $out['environments'] = array_values(array_map(static fn (array $d): array => [
                'id' => $d['environment_id'], 'revision_id' => $d['current_revision_id'],
            ], array_filter($application['deployments'] ?? [], 'is_array')));
            if (! isset($query['environment'])) {
                return response()->json($out)->header('Cache-Control', 'no-store, private');
            }
            $matches = array_values(array_filter($application['deployments'] ?? [],
                fn ($d): bool => is_array($d)
                    && ($d['environment_id'] ?? null) === $query['environment']));
            if (count($matches) !== 1) {
                return response()->json(['error' => 'catalogue_environment_not_current'], 423)
                    ->header('Cache-Control', 'no-store, private');
            }
            $revision = $catalogue->call($token, $tenant, 'getRevision', [
                'application' => $query['application'],
                'revision' => $matches[0]['current_revision_id'],
            ], environment: $query['environment']);
            $intent = $revision['intent'] ?? null;
            if (! is_array($intent)
                || ($intent['environment']['id'] ?? null) !== $query['environment']
                || ! is_array($intent['workloads'] ?? null)
                || count($intent['workloads']) > 100
                || ! preg_match('/\A[a-f0-9]{64}\z/', (string) ($revision['digest'] ?? ''))) {
                return response()->json(['error' => 'catalogue_revision_invalid'], 423)
                    ->header('Cache-Control', 'no-store, private');
            }
            $out['current'] = [
                'application_id' => $query['application'],
                'environment_id' => $query['environment'],
                'revision_id' => $revision['id'],
                'intent_sha256' => $revision['digest'],
                'workloads' => array_map(static fn (array $row): array => [
                    'id' => $row['id'], 'name' => $row['name'] ?? $row['id'],
                    'disks' => array_map(static fn (array $disk): array => [
                        'id' => $disk['id'], 'dataset_id' => $disk['dataset_id'],
                        'order' => $disk['order'],
                    ], $row['disks']),
                    'nics' => array_map(static fn (array $nic): array => [
                        'id' => $nic['id'], 'order' => $nic['order'],
                    ], $row['nics']),
                ], $intent['workloads']),
            ];
        }
        return response()->json($out)->header('Cache-Control', 'no-store, private');
    }

    public function status(Request $request, string $tenant, string $site, InventoryGateway $inventory, ?string $profile = null): JsonResponse
    {
        $inventory->call($this->session($request), $tenant, ($profile === null ? 'getMigrationReview' : 'getVmMigrationReview'), ['site' => $site, ...($profile === null ? [] : ['profile' => $profile])]);

        return response()->json(['available' => true])->header('Cache-Control', 'no-store, private');
    }

    public function command(Request $request, string $tenant, string $site, InventoryGateway $inventory, ?string $profile = null): RedirectResponse
    {
        $input = $request->validate([
            'operation' => ['required', 'in:save,confirm'], 'command_key' => ['required', 'uuid', 'lowercase'],
            'revision' => ['nullable', 'integer', 'min:1', 'max:999999999'],
            'review' => ['required_if:operation,save', 'array:source_profile_id,target_profile_id,method,datasets,owner_inputs,objectives,overrides,destination,catalogue_binding'],
            'review.catalogue_binding' => ['sometimes', 'array:application_id,environment_id,revision_id,intent_sha256,workload_id,disk_mappings,nic_mappings,disk_dispositions'],
            'review.catalogue_binding.disk_dispositions' => ['sometimes', 'array', 'max:32'],
            'review.catalogue_binding.disk_dispositions.*' => ['required', 'array:logical_device_id,native_key,disposition,owner_approval_sha256,impact_sha256'],
            'review.catalogue_binding.disk_dispositions.*.logical_device_id' => ['required', 'uuid', 'lowercase'],
            'review.catalogue_binding.disk_dispositions.*.native_key' => ['required', 'integer', 'min:0', 'max:2147483647'],
            'review.catalogue_binding.disk_dispositions.*.disposition' => ['required', 'in:uncatalogued_attested'],
            'review.catalogue_binding.disk_dispositions.*.owner_approval_sha256' => ['required', 'regex:/\\A[0-9a-f]{64}\\z/'],
            'review.catalogue_binding.disk_dispositions.*.impact_sha256' => ['required', 'regex:/\\A[0-9a-f]{64}\\z/'],
            'review.catalogue_binding.application_id' => ['required_with:review.catalogue_binding', 'uuid', 'lowercase'],
            'review.catalogue_binding.environment_id' => ['required_with:review.catalogue_binding', 'uuid', 'lowercase'],
            'review.catalogue_binding.revision_id' => ['required_with:review.catalogue_binding', 'uuid', 'lowercase'],
            'review.catalogue_binding.workload_id' => ['required_with:review.catalogue_binding', 'uuid', 'lowercase'],
            'review.catalogue_binding.intent_sha256' => ['required_with:review.catalogue_binding', 'regex:/\\A[0-9a-f]{64}\\z/'],
            'review.catalogue_binding.disk_mappings' => ['required_with:review.catalogue_binding', 'array', 'max:64'],
            'review.catalogue_binding.nic_mappings' => ['required_with:review.catalogue_binding', 'array', 'max:32'],
            'review.catalogue_binding.disk_mappings.*' => ['required', 'array:logical_device_id,native_key'],
            'review.catalogue_binding.nic_mappings.*' => ['required', 'array:logical_device_id,native_key'],
            'review.catalogue_binding.disk_mappings.*.logical_device_id' => ['required', 'uuid', 'lowercase'],
            'review.catalogue_binding.nic_mappings.*.logical_device_id' => ['required', 'uuid', 'lowercase'],
            'review.catalogue_binding.disk_mappings.*.native_key' => ['required', 'integer', 'min:0', 'max:2147483647'],
            'review.catalogue_binding.nic_mappings.*.native_key' => ['required', 'integer', 'min:0', 'max:2147483647'],
            'review.source_profile_id' => ['required_if:operation,save', 'uuid', 'lowercase'],
            'review.target_profile_id' => ['required_if:operation,save', 'uuid', 'lowercase'],
            'review.method' => ['required_if:operation,save', 'string', 'max:80'],
            'review.datasets' => ['required_if:operation,save', 'array', 'min:1', 'max:256'],
            'review.owner_inputs' => ['required_if:operation,save', 'array', 'size:8'],
            'review.objectives' => ['required_if:operation,save', 'array'],
            'review.destination' => ['sometimes', 'nullable', 'array:platform,project_id,prism_central_id,cluster_id,vpc_id,storage_container_id,category_ids,policy_ids,security_mappings,flow_mappings,vcenter_uuid,folder_id,resource_pool_id,host_id,datastore_id,guest_id,hardware_version,disks,nics,firmware'],
            'review.destination.security_mappings' => ['sometimes', 'array', 'max:64'],
            'review.destination.security_mappings.*' => ['required', 'array:source_id,destination_id'],
            'review.destination.security_mappings.*.source_id' => ['required', 'string', 'max:200'],
            'review.destination.security_mappings.*.destination_id' => ['required', 'string', 'max:200'],
            'review.destination.flow_mappings' => ['sometimes', 'array', 'max:1024'],
            'review.destination.flow_mappings.*' => ['required', 'array:source_group_id,source_rule_id,destination_rule_id'],
            'review.destination.flow_mappings.*.source_group_id' => ['required', 'string', 'max:200'],
            'review.destination.flow_mappings.*.source_rule_id' => ['required', 'string', 'max:200'],
            'review.destination.flow_mappings.*.destination_rule_id' => ['required', 'string', 'max:200'],
            'review.overrides' => ['present_if:operation,save', 'array', 'max:8'],
            'digest' => ['required_if:operation,confirm', 'nullable', 'regex:/\A[0-9a-f]{64}\z/'],
        ]);
        try {
            $inventory->call($this->session($request), $tenant,
                $input['operation'] === 'save' ? ($profile === null ? 'saveMigrationReview' : 'saveVmMigrationReview') : ($profile === null ? 'confirmMigrationReview' : 'confirmVmMigrationReview'),
                ['site' => $site, ...($profile === null ? [] : ['profile' => $profile])], $input['operation'] === 'save' ? $input['review'] : ['digest' => $input['digest']],
                $input['command_key'], isset($input['revision']) ? (int) $input['revision'] : null);
        } catch (InventoryFailure $error) {
            if (in_array($error->status, [403, 404], true)) {
                return redirect('/account')->with('tenant_notice', 'Your inventory access changed.');
            }
            throw ValidationException::withMessages(['command' => match ($error->status) {
                412 => 'The review changed. Refresh and review the current revision.',
                503 => 'The result is uncertain. Retry this exact command unchanged.',
                default => 'Review held: '.str_replace('_', ' ', $error->reason).'.',
            }, 'inventory_status' => (string) $error->status]);
        }

        return redirect('/tenants/'.$tenant.'/inventory/sites/'.$site.'/migration'.($profile === null ? '' : '/profiles/'.$profile))->with('inventory_notice',
            $input['operation'] === 'save' ? 'Migration review saved. Check all disks and owner inputs before confirming.' : 'This migration review is confirmed. Execution requires current approval and qualification.');
    }

    private function session(Request $request): string
    {
        $token = $request->session()->get('identity.token');
        if (! is_string($token)) {
            throw new InventoryFailure(403, 'access_unavailable');
        }

        return $token;
    }
}
