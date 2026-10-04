-- Selected services and newly admitted recovery use the existing B10 leases
-- and B11 intent/observation journals. These are immutable authority
-- projections, not a second operation journal or allocation database.
ALTER DOMAIN hosting_controlplane.worker_operation_kind
    DROP CONSTRAINT worker_operation_kind_allowed;
ALTER DOMAIN hosting_controlplane.worker_operation_kind
    ADD CONSTRAINT worker_operation_kind_allowed CHECK (VALUE IN (
        'DISCOVER_READ','VM_CREATE','VM_POWER','DISK_ATTACH','NETWORK_ATTACH',
        'SNAPSHOT_CREATE','SNAPSHOT_EXPORT','SNAPSHOT_IMPORT','RESTORE_DATA',
        'SOURCE_FENCE','DESTINATION_ACTIVATE','DNS_CHANGE','IPAM_RESERVE',
        'GUEST_CONFIG','POLICY_APPLY','QUOTA_CHANGE','NATIVE_CLEANUP'));

-- Every broker attempt is recorded before Vault contact. A lost wrapped or
-- unwrapped response remains visibly incomplete; expiry never completes it.
CREATE TABLE hosting_controlplane.native_credential_attempts (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    issuance_id text NOT NULL, grant_id text NOT NULL,
    role_reference text NOT NULL, creation_path text NOT NULL,
    requested_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id,tenant_id,issuance_id),
    FOREIGN KEY (organization_id,tenant_id,grant_id)
        REFERENCES hosting_controlplane.worker_grants
        (organization_id,tenant_id,grant_id) ON DELETE RESTRICT
);
CREATE TABLE hosting_controlplane.native_credential_wrappings (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    issuance_id text NOT NULL, wrapping_digest text NOT NULL CHECK (wrapping_digest ~ '^[0-9a-f]{64}$'),
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (organization_id,tenant_id,issuance_id),
    FOREIGN KEY (organization_id,tenant_id,issuance_id)
        REFERENCES hosting_controlplane.native_credential_attempts
        (organization_id,tenant_id,issuance_id) ON DELETE RESTRICT
);
CREATE TABLE hosting_controlplane.native_credential_leases (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    issuance_id text NOT NULL, lease_digest text NOT NULL CHECK (lease_digest ~ '^[0-9a-f]{64}$'),
    lease_id text NOT NULL CHECK (length(lease_id) BETWEEN 1 AND 4096),
    consumed_at timestamptz NOT NULL DEFAULT clock_timestamp(), expires_at timestamptz NOT NULL,
    PRIMARY KEY (organization_id,tenant_id,issuance_id),
    UNIQUE (organization_id,tenant_id,lease_digest),
    FOREIGN KEY (organization_id,tenant_id,issuance_id)
        REFERENCES hosting_controlplane.native_credential_wrappings
        (organization_id,tenant_id,issuance_id) ON DELETE RESTRICT
);
CREATE TRIGGER credential_attempts_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_credential_attempts FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER credential_wrappings_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_credential_wrappings FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER credential_leases_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.native_credential_leases FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TABLE hosting_controlplane.planned_service_bindings (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    lease_key text NOT NULL,
    job_id text NOT NULL,
    resource_id text NOT NULL,
    step_id text NOT NULL,
    operation_kind text NOT NULL CHECK (operation_kind IN
        ('IPAM_RESERVE', 'DNS_CHANGE', 'QUOTA_CHANGE')),
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (organization_id, tenant_id, lease_key),
    FOREIGN KEY (organization_id, tenant_id, lease_key)
        REFERENCES hosting_controlplane.native_operation_leases
        (organization_id, tenant_id, lease_key) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tenant_id, job_id, resource_id)
        REFERENCES hosting_controlplane.planned_resource_ownership
        (organization_id, tenant_id, job_id, resource_id) ON DELETE RESTRICT
);
CREATE TRIGGER planned_service_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.planned_service_bindings FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

CREATE OR REPLACE FUNCTION hosting_controlplane.guard_planned_operation_scope()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.planned_resource_id IS NULL THEN RETURN NEW; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
         WHERE (p.organization_id,p.tenant_id,p.job_id,p.resource_id,
                p.platform_family,p.endpoint_id,p.native_scope_id,p.resource_kind,
                p.worker_id,p.owner_epoch,p.security_domain_id) =
               (NEW.organization_id,NEW.tenant_id,NEW.job_id,NEW.planned_resource_id,
                NEW.platform_family,NEW.endpoint_id,NEW.native_scope_id,NEW.resource_kind,
                NEW.worker_id,NEW.owner_epoch,NEW.security_domain_id)
    ) THEN RAISE EXCEPTION 'Planned operation must project its exact immutable owner'; END IF;
    IF TG_TABLE_NAME = 'native_operation_leases' THEN
        IF NOT EXISTS (
            SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
             WHERE (p.organization_id,p.tenant_id,p.job_id,p.resource_id) =
                   (NEW.organization_id,NEW.tenant_id,NEW.job_id,NEW.planned_resource_id)
               AND p.site_id=NEW.site_id AND NEW.expires_at<=p.lease_expires_at
        ) THEN RAISE EXCEPTION 'Planned lease exceeds its owner scope or deadline'; END IF;
    ELSIF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.native_operation_leases l
        JOIN hosting_controlplane.planned_resource_ownership p
          ON (p.organization_id,p.tenant_id,p.job_id,p.resource_id) =
             (l.organization_id,l.tenant_id,l.job_id,l.planned_resource_id)
         WHERE (l.organization_id,l.tenant_id,l.lease_key,l.operation_id,p.job_id,
                p.resource_id,p.workload_id) =
               (NEW.organization_id,NEW.tenant_id,NEW.lease_key,NEW.operation_id,
                NEW.job_id,NEW.planned_resource_id,NEW.workload_id)
           AND ((NEW.operation_kind='VM_CREATE' AND p.request_digest=NEW.request_digest
                AND NOT EXISTS (SELECT 1 FROM hosting_controlplane.planned_service_bindings x
                    WHERE (x.organization_id,x.tenant_id,x.lease_key)=
                          (NEW.organization_id,NEW.tenant_id,NEW.lease_key)))
             OR EXISTS (
                SELECT 1 FROM hosting_controlplane.planned_service_bindings s
                 WHERE (s.organization_id,s.tenant_id,s.lease_key,s.job_id,s.resource_id,
                        s.step_id,s.operation_kind,s.request_digest) =
                       (NEW.organization_id,NEW.tenant_id,NEW.lease_key,NEW.job_id,
                        NEW.planned_resource_id,NEW.step_id,NEW.operation_kind,NEW.request_digest)))
    ) THEN RAISE EXCEPTION 'Planned effect must match its exact selected lease and request'; END IF;
    RETURN NEW;
END;
$$;

CREATE TABLE hosting_controlplane.resource_recovery_bindings (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    recovery_job_id text NOT NULL,
    original_job_id text NOT NULL,
    original_plan_digest text NOT NULL CHECK (original_plan_digest ~ '^[0-9a-f]{64}$'),
    original_selection_digest text NOT NULL CHECK (original_selection_digest ~ '^[0-9a-f]{64}$'),
    resource_bundle_digest text NOT NULL CHECK (resource_bundle_digest ~ '^[0-9a-f]{64}$'),
    reservation_digest text NOT NULL CHECK (reservation_digest ~ '^[0-9a-f]{64}$'),
    original_operations jsonb NOT NULL CHECK (jsonb_typeof(original_operations)='array'
        AND jsonb_array_length(original_operations)>0),
    binding_digest text NOT NULL CHECK (binding_digest ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id,tenant_id,recovery_job_id),
    CHECK (original_job_id <> recovery_job_id),
    FOREIGN KEY (organization_id,tenant_id,recovery_job_id)
        REFERENCES hosting_controlplane.operation_jobs
        (organization_id,tenant_id,job_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,original_job_id)
        REFERENCES hosting_controlplane.operation_jobs
        (organization_id,tenant_id,job_id) ON DELETE RESTRICT
);
CREATE TRIGGER resource_recovery_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.resource_recovery_bindings FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

DO $$ DECLARE selected_table text; BEGIN
    FOREACH selected_table IN ARRAY ARRAY['planned_service_bindings','resource_recovery_bindings',
        'native_credential_attempts','native_credential_wrappings','native_credential_leases'] LOOP
        EXECUTE format('ALTER TABLE hosting_controlplane.%I ENABLE ROW LEVEL SECURITY',selected_table);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I FORCE ROW LEVEL SECURITY',selected_table);
        EXECUTE format('CREATE POLICY tenant_scope ON hosting_controlplane.%I '
            || 'USING (organization_id=current_setting(''app.organization_id'',true) '
            || 'AND tenant_id=current_setting(''app.tenant_id'',true)) '
            || 'WITH CHECK (organization_id=current_setting(''app.organization_id'',true) '
            || 'AND tenant_id=current_setting(''app.tenant_id'',true))', selected_table);
        EXECUTE format('REVOKE ALL ON hosting_controlplane.%I FROM PUBLIC',selected_table);
    END LOOP;
END $$;
