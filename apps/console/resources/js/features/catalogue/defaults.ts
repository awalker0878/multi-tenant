import type { Intent } from './contracts';
export function workload(): Intent['workloads'][number] {
  return { id: crypto.randomUUID(), name: '', role: 'application', wsd: { id: '', version: 1 }, security_domain: { id: '', version: 1 },
    compute: { vcpus: 2, memory_mib: 4096, architecture: 'x86_64' },
    guest: { os: 'linux', image: '', firmware: 'uefi', secure_boot: true, hardening_profile: '' },
    disks: [{ id: crypto.randomUUID(), order: 0, size_gib: 40, storage_class: 'standard', boot: true, dataset_id: null, encryption: 'required' }],
    nics: [{ id: crypto.randomUUID(), order: 0, security_domain_id: '', address_families: ['ipv4'], address_intent: 'reserved', network_class: 'private' }],
    requirements: [], failure_domain: { group: '', mode: 'independent', strength: 'required' } };
}
export function intent(owner: string): Intent {
  return { schema_version: 1, deployment_id: crypto.randomUUID(), environment: { id: '', version: 1 }, service_owner_id: owner,
    acceptance_criteria: [''], workloads: [workload()], datasets: [], dependencies: [], services: [], requirements: [] };
}
export function differences(before: unknown, after: unknown, path = ''): Array<{ path: string; before: string; after: string }> {
  if (JSON.stringify(before) === JSON.stringify(after)) return [];
  if (before !== null && after !== null && typeof before === 'object' && typeof after === 'object') {
    const a = before as Record<string, unknown>, b = after as Record<string, unknown>;
    return [...new Set([...Object.keys(a), ...Object.keys(b)])].flatMap(key => differences(a[key], b[key], path ? `${path}.${key}` : key));
  }
  return [{ path, before: before === undefined ? 'Not present' : JSON.stringify(before), after: after === undefined ? 'Not present' : JSON.stringify(after) }];
}
