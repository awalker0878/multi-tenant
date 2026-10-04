-- One explicit Glance image projection of the existing planned B10 owner and
-- B11 journal. Logical image names are not invented native ownership. Genuine
-- UUIDs enter only as original response receipts and independent observations.
ALTER TABLE hosting_controlplane.planned_resource_ownership
    DROP CONSTRAINT planned_resource_ownership_resource_kind_check;
ALTER TABLE hosting_controlplane.planned_resource_ownership
    ADD CONSTRAINT planned_resource_ownership_resource_kind_check
        CHECK (resource_kind IN ('vm','deployment','image'));

CREATE TABLE hosting_controlplane.planned_image_inputs (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    job_id text NOT NULL, resource_id text NOT NULL,
    cold_selection_digest text NOT NULL CHECK (cold_selection_digest ~ '^[0-9a-f]{64}$'),
    source_operation_id text NOT NULL,
    capture_digest text NOT NULL CHECK (capture_digest ~ '^[0-9a-f]{64}$'),
    source_snapshot_moid text NOT NULL CHECK (source_snapshot_moid ~ '^snapshot-[1-9][0-9]{0,15}$'),
    disk_id text NOT NULL, device_key integer NOT NULL CHECK (device_key>=0),
    nfc_key text NOT NULL,
    output_sha256 text NOT NULL CHECK (output_sha256 ~ '^[0-9a-f]{64}$'),
    output_sha512 text NOT NULL CHECK (output_sha512 ~ '^[0-9a-f]{128}$'),
    output_bytes bigint NOT NULL CHECK (output_bytes>0),
    virtual_bytes bigint NOT NULL CHECK (virtual_bytes>0),
    image_name text NOT NULL,
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (organization_id,tenant_id,job_id,resource_id),
    UNIQUE (organization_id,tenant_id,job_id,cold_selection_digest,disk_id),
    FOREIGN KEY (organization_id,tenant_id,job_id,resource_id)
        REFERENCES hosting_controlplane.planned_resource_ownership
        (organization_id,tenant_id,job_id,resource_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,source_operation_id)
        REFERENCES hosting_controlplane.native_operation_intents
        (organization_id,tenant_id,operation_id) ON DELETE RESTRICT
);
CREATE TABLE hosting_controlplane.planned_image_bindings (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    lease_key text NOT NULL, job_id text NOT NULL, resource_id text NOT NULL,
    step_id text NOT NULL,
    phase text NOT NULL CHECK (phase IN ('CREATE','UPLOAD')),
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (organization_id,tenant_id,lease_key),
    UNIQUE (organization_id,tenant_id,job_id,resource_id,phase),
    FOREIGN KEY (organization_id,tenant_id,lease_key)
        REFERENCES hosting_controlplane.native_operation_leases
        (organization_id,tenant_id,lease_key) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,job_id,resource_id)
        REFERENCES hosting_controlplane.planned_image_inputs
        (organization_id,tenant_id,job_id,resource_id) ON DELETE RESTRICT
);
CREATE TABLE hosting_controlplane.planned_image_receipts (
    organization_id text NOT NULL, tenant_id text NOT NULL,
    operation_id text NOT NULL, job_id text NOT NULL, resource_id text NOT NULL,
    native_image_id text NOT NULL CHECK (native_image_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
    native_request_id text NOT NULL CHECK (native_request_id ~ '^req-[0-9a-f-]{36}$'),
    received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id,tenant_id,operation_id),
    UNIQUE (organization_id,tenant_id,job_id,resource_id),
    FOREIGN KEY (organization_id,tenant_id,operation_id)
        REFERENCES hosting_controlplane.native_operation_intents
        (organization_id,tenant_id,operation_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,job_id,resource_id)
        REFERENCES hosting_controlplane.planned_image_inputs
        (organization_id,tenant_id,job_id,resource_id) ON DELETE RESTRICT
);
-- Glance IDs are image observations, not VM/disk NativeBindings. These columns
-- keep actual image facts in the original native observation owner.
ALTER TABLE hosting_controlplane.native_operation_observations
    ADD COLUMN created_native_image_id text,
    ADD CONSTRAINT native_image_observation CHECK (
        created_native_image_id IS NULL OR (outcome='EFFECT_PRESENT'
            AND created_native_image_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            AND created_native_bindings IS NULL));

CREATE FUNCTION hosting_controlplane.guard_planned_image_input()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
        JOIN hosting_controlplane.native_operation_intents source
          ON (source.organization_id,source.tenant_id,source.operation_id)=
             (NEW.organization_id,NEW.tenant_id,NEW.source_operation_id)
         WHERE (p.organization_id,p.tenant_id,p.job_id,p.resource_id,p.request_digest)=
               (NEW.organization_id,NEW.tenant_id,NEW.job_id,NEW.resource_id,NEW.request_digest)
           AND p.resource_kind='image' AND p.platform_family='openstack'
           AND source.job_id=p.job_id AND source.workload_id=p.workload_id
           AND source.platform_family='vmware' AND source.resource_kind='vm'
           AND source.operation_kind='SNAPSHOT_EXPORT'
           AND source.state='RESOLVED' AND source.outcome='EFFECT_PRESENT'
           AND EXISTS (SELECT 1 FROM hosting_controlplane.native_operation_observations o
                WHERE (o.organization_id,o.tenant_id,o.operation_id)=
                      (source.organization_id,source.tenant_id,source.operation_id)
                  AND o.outcome='EFFECT_PRESENT' AND o.native_quiesced
                  AND o.observer_subject<>source.worker_id
                  AND o.native_task_id=source.native_task_id)
    ) THEN RAISE EXCEPTION 'Image input requires its exact original independently observed native export'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planned_image_input BEFORE INSERT ON hosting_controlplane.planned_image_inputs
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_image_input();

CREATE FUNCTION hosting_controlplane.guard_planned_image_binding()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.native_operation_leases l
        JOIN hosting_controlplane.planned_resource_ownership p
          ON (p.organization_id,p.tenant_id,p.job_id,p.resource_id)=
             (l.organization_id,l.tenant_id,l.job_id,l.planned_resource_id)
        JOIN hosting_controlplane.planned_image_inputs i
          ON (i.organization_id,i.tenant_id,i.job_id,i.resource_id)=
             (p.organization_id,p.tenant_id,p.job_id,p.resource_id)
         WHERE (l.organization_id,l.tenant_id,l.lease_key,p.job_id,p.resource_id)=
               (NEW.organization_id,NEW.tenant_id,NEW.lease_key,NEW.job_id,NEW.resource_id)
           AND p.resource_kind='image' AND l.native_id IS NULL
    ) THEN RAISE EXCEPTION 'Image action must project its exact original logical image owner'; END IF;
    IF NEW.phase='UPLOAD' AND NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.planned_image_bindings create_action
        JOIN hosting_controlplane.native_operation_intents create_intent
          ON (create_intent.organization_id,create_intent.tenant_id,create_intent.lease_key)=
             (create_action.organization_id,create_action.tenant_id,create_action.lease_key)
        JOIN hosting_controlplane.planned_image_receipts receipt
          ON (receipt.organization_id,receipt.tenant_id,receipt.operation_id)=
             (create_intent.organization_id,create_intent.tenant_id,create_intent.operation_id)
         WHERE (create_action.organization_id,create_action.tenant_id,create_action.job_id,create_action.resource_id)=
               (NEW.organization_id,NEW.tenant_id,NEW.job_id,NEW.resource_id)
           AND create_action.phase='CREATE' AND create_intent.state='RESOLVED'
           AND create_intent.outcome='EFFECT_PRESENT'
           AND EXISTS (SELECT 1 FROM hosting_controlplane.native_operation_observations o
                WHERE (o.organization_id,o.tenant_id,o.operation_id,o.created_native_image_id)=
                      (receipt.organization_id,receipt.tenant_id,receipt.operation_id,receipt.native_image_id)
                  AND o.outcome='EFFECT_PRESENT' AND o.native_quiesced
                  AND o.observer_subject<>create_intent.worker_id)
    ) THEN RAISE EXCEPTION 'Image upload needs the original independently observed create UUID'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planned_image_binding BEFORE INSERT ON hosting_controlplane.planned_image_bindings
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_image_binding();

CREATE FUNCTION hosting_controlplane.guard_planned_image_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.native_operation_intents original
        JOIN hosting_controlplane.planned_image_bindings selected
          ON (selected.organization_id,selected.tenant_id,selected.lease_key)=
             (original.organization_id,original.tenant_id,original.lease_key)
         WHERE (original.organization_id,original.tenant_id,original.operation_id,original.job_id,original.planned_resource_id)=
               (NEW.organization_id,NEW.tenant_id,NEW.operation_id,NEW.job_id,NEW.resource_id)
           AND selected.phase='CREATE' AND original.operation_kind='SNAPSHOT_IMPORT'
           AND original.resource_kind='image' AND original.state IN ('IN_FLIGHT','UNCERTAIN')
    ) THEN RAISE EXCEPTION 'Only the original claimed Glance create can retain a genuine response UUID'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planned_image_receipt BEFORE INSERT ON hosting_controlplane.planned_image_receipts
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_image_receipt();

CREATE FUNCTION hosting_controlplane.guard_planned_image_observation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.created_native_image_id IS NULL THEN RETURN NEW; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.native_operation_intents original
        JOIN hosting_controlplane.planned_image_receipts receipt
          ON (receipt.organization_id,receipt.tenant_id,receipt.job_id,receipt.resource_id)=
             (original.organization_id,original.tenant_id,original.job_id,original.planned_resource_id)
         WHERE (original.organization_id,original.tenant_id,original.operation_id,receipt.native_image_id)=
               (NEW.organization_id,NEW.tenant_id,NEW.operation_id,NEW.created_native_image_id)
           AND original.resource_kind='image' AND original.operation_kind='SNAPSHOT_IMPORT'
           AND original.worker_id<>NEW.observer_subject AND NEW.outcome='EFFECT_PRESENT'
           AND NEW.native_quiesced AND NEW.native_task_id IS NULL
    ) THEN RAISE EXCEPTION 'Image observation must retain the genuine UUID of its original native create'; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER planned_image_observation BEFORE INSERT ON hosting_controlplane.native_operation_observations
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_planned_image_observation();

CREATE OR REPLACE FUNCTION hosting_controlplane.guard_planned_operation_scope()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.planned_resource_id IS NULL THEN RETURN NEW; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
         WHERE (p.organization_id,p.tenant_id,p.job_id,p.resource_id,
                p.platform_family,p.endpoint_id,p.native_scope_id,p.resource_kind,
                p.worker_id,p.owner_epoch,p.security_domain_id)=
               (NEW.organization_id,NEW.tenant_id,NEW.job_id,NEW.planned_resource_id,
                NEW.platform_family,NEW.endpoint_id,NEW.native_scope_id,NEW.resource_kind,
                NEW.worker_id,NEW.owner_epoch,NEW.security_domain_id)
    ) THEN RAISE EXCEPTION 'Planned operation must project its exact immutable owner'; END IF;
    IF TG_TABLE_NAME='native_operation_leases' THEN
        IF NOT EXISTS (
            SELECT 1 FROM hosting_controlplane.planned_resource_ownership p
             WHERE (p.organization_id,p.tenant_id,p.job_id,p.resource_id)=
                   (NEW.organization_id,NEW.tenant_id,NEW.job_id,NEW.planned_resource_id)
               AND p.site_id=NEW.site_id AND NEW.expires_at<=p.lease_expires_at
        ) THEN RAISE EXCEPTION 'Planned lease exceeds its owner scope or deadline'; END IF;
    ELSIF NOT EXISTS (
        SELECT 1 FROM hosting_controlplane.native_operation_leases l
        JOIN hosting_controlplane.planned_resource_ownership p
          ON (p.organization_id,p.tenant_id,p.job_id,p.resource_id)=
             (l.organization_id,l.tenant_id,l.job_id,l.planned_resource_id)
         WHERE (l.organization_id,l.tenant_id,l.lease_key,l.operation_id,p.job_id,p.resource_id,p.workload_id)=
               (NEW.organization_id,NEW.tenant_id,NEW.lease_key,NEW.operation_id,NEW.job_id,
                NEW.planned_resource_id,NEW.workload_id)
           AND ((p.resource_kind IN ('vm','deployment') AND NEW.operation_kind='VM_CREATE'
                 AND p.request_digest=NEW.request_digest AND NOT EXISTS (
                    SELECT 1 FROM hosting_controlplane.planned_service_bindings x
                     WHERE (x.organization_id,x.tenant_id,x.lease_key)=
                           (NEW.organization_id,NEW.tenant_id,NEW.lease_key)))
             OR (p.resource_kind IN ('vm','deployment') AND EXISTS (
                 SELECT 1 FROM hosting_controlplane.planned_service_bindings s
                  WHERE (s.organization_id,s.tenant_id,s.lease_key,s.job_id,s.resource_id,
                         s.step_id,s.operation_kind,s.request_digest)=
                        (NEW.organization_id,NEW.tenant_id,NEW.lease_key,NEW.job_id,
                         NEW.planned_resource_id,NEW.step_id,NEW.operation_kind,NEW.request_digest)))
             OR (p.resource_kind='image' AND NEW.operation_kind='SNAPSHOT_IMPORT' AND EXISTS (
                 SELECT 1 FROM hosting_controlplane.planned_image_bindings image
                  WHERE (image.organization_id,image.tenant_id,image.lease_key,image.job_id,image.resource_id,
                         image.step_id,image.request_digest)=
                        (NEW.organization_id,NEW.tenant_id,NEW.lease_key,NEW.job_id,
                         NEW.planned_resource_id,NEW.step_id,NEW.request_digest))))
    ) THEN RAISE EXCEPTION 'Planned effect must match its exact selected lease and request'; END IF;
    RETURN NEW;
END;
$$;

DO $$ DECLARE selected_table text; BEGIN
    FOREACH selected_table IN ARRAY ARRAY['planned_image_inputs','planned_image_bindings','planned_image_receipts'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_image_projection BEFORE UPDATE OR DELETE '
            || 'ON hosting_controlplane.%I FOR EACH ROW EXECUTE FUNCTION '
            || 'hosting_controlplane.prevent_append_only_changes()',selected_table);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I ENABLE ROW LEVEL SECURITY',selected_table);
        EXECUTE format('ALTER TABLE hosting_controlplane.%I FORCE ROW LEVEL SECURITY',selected_table);
        EXECUTE format('CREATE POLICY tenant_scope ON hosting_controlplane.%I '
            || 'USING (organization_id=current_setting(''app.organization_id'',true) '
            || 'AND tenant_id=current_setting(''app.tenant_id'',true)) '
            || 'WITH CHECK (organization_id=current_setting(''app.organization_id'',true) '
            || 'AND tenant_id=current_setting(''app.tenant_id'',true))',selected_table);
        EXECUTE format('REVOKE ALL ON hosting_controlplane.%I FROM PUBLIC',selected_table);
    END LOOP;
END $$;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_planned_image_input() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_planned_image_binding() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_planned_image_receipt() FROM PUBLIC;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_planned_image_observation() FROM PUBLIC;
