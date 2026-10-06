<?php

declare(strict_types=1);

namespace App\Domain\IntentRevisions;

final class IntentDocument
{
    /** Schema-validated, complete effective input.
     * @param array<string,mixed> $intent */
    public static function check(array $intent): void
    {
        self::portableIntegers($intent, 'intent');
        $workloads = [];
        $datasets = [];
        foreach ($intent['datasets'] as $i => $dataset) {
            self::unique($datasets, $dataset['id'], "datasets.$i.id");
        }
        $deviceIds = [];
        foreach ($intent['workloads'] as $i => $workload) {
            self::unique($workloads, $workload['id'], "workloads.$i.id");
            foreach (['disks', 'nics'] as $devices) {
                $orders = [];
                foreach ($workload[$devices] as $j => $device) {
                    self::unique($deviceIds, $device['id'], "workloads.$i.$devices.$j.id");
                    self::unique($orders, (string) $device['order'], "workloads.$i.$devices.$j.order");
                    if ($devices === 'nics' && $device['security_domain_id'] !== $workload['security_domain']['id']) {
                        throw new IntentFailure('nic_domain_mismatch', 422, "workloads.$i.nics.$j.security_domain_id");
                    }
                    if ($devices === 'disks' && $device['dataset_id'] !== null && ! isset($datasets[$device['dataset_id']])) {
                        throw new IntentFailure('dangling_dataset', 422, "workloads.$i.disks.$j.dataset_id");
                    }
                }
                $actual = array_map('intval', array_keys($orders));
                sort($actual);
                if ($actual !== ($actual === [] ? [] : range(0, count($actual) - 1))) {
                    throw new IntentFailure('device_order_gap', 422, "workloads.$i.$devices");
                }
            }
            if (count(array_filter($workload['disks'], fn (array $d): bool => $d['boot'])) !== 1) {
                throw new IntentFailure('one_boot_disk_required', 422, "workloads.$i.disks");
            }
        }
        $byId = array_column($intent['workloads'], null, 'id');
        $graphs = ['startup' => [], 'shutdown' => []];
        $edges = [];
        foreach ($intent['dependencies'] as $i => $edge) {
            if (! isset($workloads[$edge['from']],$workloads[$edge['to']]) || $edge['from'] === $edge['to']) {
                throw new IntentFailure('dangling_or_self_dependency', 422, "dependencies.$i");
            }
            self::unique($edges, CanonicalJson::encode([$edge['from'], $edge['to'], $edge['kind'], $edge['protocol'], $edge['port']]), "dependencies.$i");
            if ($edge['dataset_id'] !== null && ! isset($datasets[$edge['dataset_id']])) {
                throw new IntentFailure('dangling_dataset', 422, "dependencies.$i.dataset_id");
            }
            if ($edge['kind'] !== 'communication') {
                $graphs[$edge['kind']][$edge['from']][] = $edge['to'];
            } elseif ($byId[$edge['from']]['security_domain']['id'] !== $byId[$edge['to']]['security_domain']['id'] && ! $edge['controlled_interface']) {
                throw new IntentFailure('controlled_interface_required', 422, "dependencies.$i.controlled_interface");
            }
            if (in_array($edge['protocol'], ['tcp', 'udp'], true) !== ($edge['port'] !== null)) {
                throw new IntentFailure('protocol_port_mismatch', 422, "dependencies.$i.port");
            }
        }
        foreach ($graphs as $graph) {
            $visited = [];
            $active = [];
            foreach (array_keys($workloads) as $id) {
                self::visit((string) $id, $graph, $visited, $active);
            }
        }
        $services = [];
        foreach ($intent['services'] as $i => $service) {
            self::unique($services, $service['name'], "services.$i.name");
            if (! isset($workloads[$service['workload_id']])) {
                throw new IntentFailure('dangling_service_workload', 422, "services.$i.workload_id");
            }
        }
    }

    // Complete snapshots must survive PHP/Python/JavaScript transport unchanged.
    // Use text for identifiers or exact integers beyond the interoperable range.
    private static function portableIntegers(mixed $value, string $field): void
    {
        if ((is_int($value) || is_float($value)) && ($value > 9007199254740991 || $value < -9007199254740991)) {
            throw new IntentFailure('integer_outside_interoperable_range', 422, $field);
        }
        if (is_array($value)) {
            foreach ($value as $key => $child) {
                self::portableIntegers($child, $field.'.'.$key);
            }
        }
    }

    /**
     * @param array<string|int,bool> $seen */
    private static function unique(array &$seen, string $key, string $field): void
    {
        if (isset($seen[$key])) {
            throw new IntentFailure('duplicate_identity', 422, $field);
        } $seen[$key] = true;
    }

    /**
     * @param array<string,list<string>> $graph
     * @param array<string,bool> $visited
     * @param array<string,bool> $active */
    private static function visit(string $id, array $graph, array &$visited, array &$active): void
    {
        if (isset($active[$id])) {
            throw new IntentFailure('dependency_cycle', 422, 'dependencies');
        }
        if (isset($visited[$id])) {
            return;
        } $active[$id] = true;
        foreach ($graph[$id] ?? [] as $next) {
            self::visit($next, $graph, $visited, $active);
        }
        unset($active[$id]);
        $visited[$id] = true;
    }
}
