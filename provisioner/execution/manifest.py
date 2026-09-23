"""The reviewed-plan manifest.

A plan identity is only useful for approval if it binds every decision that changes
what would be executed. The manifest is that complete, canonical projection: it
names each reviewed decision term and digests the whole document, so an external
approval that cites the manifest digest provably cites the exact plan, and a change
to any approval-relevant term changes the identity.

The manifest holds no volatile timestamp, no checkout property and no
owner-provisioned free text: it is reproducible from the reviewed inputs alone.
Terms that would be derived from the manifest itself (the delivery `plan_digest`
and the operation identities) are excluded, so the identity is never
self-referential.
"""
from __future__ import annotations

from provisioner.domain.request import digest

MANIFEST_FORMAT = 'hosting-reviewed-plan-manifest/1'

#: The manifest's own terms, in the order a reviewer reads them.
TERMS = ('format', 'generation', 'request', 'request_identity', 'resolution', 'policy',
         'inventory', 'placement', 'qualification', 'product_tuple', 'capacity',
         'addresses', 'service_bindings', 'desired_state', 'environment',
         'compiled_inputs', 'terraform', 'ansible', 'delivery', 'classification')

#: Terraform scope keys the manifest binds. `backend` is excluded deliberately: it is
#: the free text an owner provisions against the reviewed state key, not a reviewed
#: decision, and binding it would make the plan identity depend on owner state.
TERRAFORM_SCOPE_KEYS = ('scope', 'root', 'input', 'state_key', 'catalog_id',
                        'owner_scope', 'status')

#: The delivery graph keys the manifest binds, excluding every derived identity.
DELIVERY_KEYS = ('status', 'blocking', 'terraform', 'operations')
DELIVERY_OPERATION_KEYS = ('name', 'owner', 'status', 'blocking', 'details')


def request_identity(request) -> str:
    """The normalized request identity, as distinct from the request source digest.

    The request digest identifies the file that was read; this identifies the
    normalized content that was reviewed. Two differently-formatted but equivalent
    requests share one identity here.
    """
    return digest({'apiVersion': request.api_version, 'kind': request.kind,
                   'metadata': request.metadata, 'spec': request.spec})


def inventory_reference(inventory) -> dict:
    """The reviewed inventory snapshot this decision was made over."""
    if inventory is None:
        return {'digest': '', 'status': 'UNRECORDED', 'origin': '', 'authoritative': False}
    return {'digest': inventory.document_digest, 'status': inventory.status,
            'origin': inventory.origin, 'authoritative': inventory.authoritative}


def address_intent(desired_state) -> list[dict]:
    """Every reserved prefix, gateway host number and workload address, per domain."""
    return [{'zone': domain.zone, 'prefix': domain.prefix,
             'gateway_host_number': domain.gateway_host_number,
             'addresses': sorted(workload.address for workload in domain.workloads)}
            for domain in sorted(desired_state.domains, key=lambda d: d.prefix)]


def capacity_intent(desired_state) -> dict:
    """Every reservation, including the demand and the committed-after position."""
    return {zone: reservation
            for zone, reservation in sorted(desired_state.reservations.items())}


def service_binding_intent(desired_state) -> list[dict]:
    """Every service binding, including its endpoints and binding class."""
    return [dict(binding) for binding in desired_state.service_bindings]


def compiled_input_intent(compiled: dict) -> dict:
    """The identity of every compiled input the existing compiler accepted."""
    return {name: digest(value) for name, value in sorted(compiled.items())}


def terraform_intent(scopes) -> list[dict]:
    """The reviewed Terraform scope, root, input and state-key bindings."""
    return [{key: (dict(scope[key]) if key == 'scope' else scope.get(key, ''))
             for key in TERRAFORM_SCOPE_KEYS} for scope in scopes]


def ansible_intent(scopes) -> list[dict]:
    """The reviewed Ansible scope bindings."""
    return [dict(scope) for scope in scopes]


def delivery_intent(graph: str) -> dict:
    """The reviewed delivery graph, by identity."""
    return {'graph': graph, 'keys': list(DELIVERY_KEYS)}


def classification(desired_state) -> dict:
    """The approval-relevant change classification of this decision.

    A greenfield create never destroys anything, so a production plan is declared
    *disruptive* (it changes a production environment) and explicitly not
    *destructive* and not a *rebuild*. The repository has no replacement or destroy
    intent yet, so `destructive` and `rebuild` are declared false here and a future
    change-intent model must set them from reviewed input.
    """
    lifecycle = desired_state.lifecycle
    return {'lifecycle': lifecycle, 'disruptive': lifecycle == 'production',
            'destructive': False, 'rebuild': False}


def build(plan, delivery_graph: str = '') -> dict:
    """The complete reviewed-plan manifest of one plan.

    Every term is either a reviewed decision or a digest of one. Nothing here is
    derived from the plan identity, so the manifest can be computed before that
    identity exists.
    """
    return {
        'format': MANIFEST_FORMAT,
        'generation': plan.generation,
        'request': {'source': plan.request.source, 'digest': plan.request.digest},
        'request_identity': request_identity(plan.request),
        'resolution': {'profiles': dict(plan.resolution.profiles),
                       'profile_versions': dict(plan.resolution.profile_versions),
                       'catalog_versions': dict(plan.resolution.catalog_versions),
                       'catalog_digest': plan.resolution.catalog_digest},
        'policy': dict(plan.policy),
        'inventory': inventory_reference(plan.inventory),
        'placement': plan.decision.digest,
        'qualification': plan.decision.qualification_identity,
        'product_tuple': plan.decision.product_tuple,
        'capacity': capacity_intent(plan.desired_state),
        'addresses': address_intent(plan.desired_state),
        'service_bindings': service_binding_intent(plan.desired_state),
        'desired_state': plan.desired_state.digest,
        'environment': digest(plan.environment),
        'compiled_inputs': compiled_input_intent(plan.compiled),
        'terraform': terraform_intent(plan.terraform_scopes),
        'ansible': ansible_intent(plan.ansible_scopes),
        'delivery': delivery_intent(delivery_graph),
        'classification': classification(plan.desired_state),
    }


def digest_of(manifest: dict) -> str:
    """The canonical identity of a reviewed-plan manifest."""
    return digest(manifest)


def review(manifest: dict) -> dict:
    """A reviewer-facing projection naming the terms that decide approval.

    The projection carries the manifest digest, so an approval that cites either the
    manifest or this projection cites the same complete plan.
    """
    return {'format': manifest['format'],
            'digest': digest_of(manifest),
            'generation': manifest['generation'],
            'request_digest': manifest['request']['digest'],
            'request_identity': manifest['request_identity'],
            'inventory': manifest['inventory'],
            'placement': manifest['placement'],
            'qualification': manifest['qualification'],
            'product_tuple': manifest['product_tuple'],
            'profile_versions': manifest['resolution']['profile_versions'],
            'catalog_versions': manifest['resolution']['catalog_versions'],
            'catalog_digest': manifest['resolution']['catalog_digest'],
            'rules_digest': manifest['policy'].get('rules_digest', ''),
            'rules_failed': list(manifest['policy'].get('rules_failed', [])),
            'desired_state': manifest['desired_state'],
            'environment': manifest['environment'],
            'terraform': [scope['state_key'] for scope in manifest['terraform']],
            'ansible': [scope.get('profile', '') for scope in manifest['ansible']],
            'delivery': manifest['delivery']['graph'],
            'classification': manifest['classification']}