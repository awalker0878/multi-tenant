<?php

declare(strict_types=1);

namespace App\Domain\Qualification;

/** Generated definition metadata; Assurance decisions remain independent. */
final class CapabilityDefinitions
{
    public const string SHA256 = 'af7342d6e03b5f1c8ef2bacd11260bc2831611b01a52ec58340ff17f297063ec';

    public const string VERSION = '1.0.0';

    public const array PLATFORMS = ['vmware', 'ahv', 'openstack'];

    public const array METHODS = ['cold_export', 'rebuild_restore', 'application_delta', 'file_delta', 'block_replication'];

    public const array LEGACY_METHODS = ['VM_COLD_EXPORT', 'APPLICATION_REBUILD_RESTORE', 'VM_SNAPSHOT_BASELINE_APP_DELTA', 'VM_SNAPSHOT_BASELINE_FILE_DELTA', 'EXTERNAL_BLOCK_REPLICATION'];
}
