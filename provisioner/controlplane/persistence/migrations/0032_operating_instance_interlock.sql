-- A restored database cannot acquire native work by overriding a read-only
-- session default. This global interlock is separate from tenant authority and
-- B48's retained-scope handover. Runtime roles get SELECT only on this table.
-- Dedicated operating custody receives UPDATE; it must verify independent
-- original evidence through operations.instance before activating an instance.
CREATE TABLE hosting_controlplane.operating_instance (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    instance_id text NOT NULL CHECK (instance_id ~ '^[0-9a-f]{32}$'),
    database_oid oid NOT NULL,
    database_system_identifier text NOT NULL CHECK (database_system_identifier ~ '^[0-9]{1,20}$'),
    generation bigint NOT NULL CHECK (generation > 0),
    mode text NOT NULL CHECK (mode IN ('UNCOMMISSIONED','OBSERVATION_ONLY','DRAINED','ACTIVE')),
    organization_id text,
    tenant_id text,
    source_commit text CHECK (source_commit ~ '^[0-9a-f]{40}$'),
    artifact_sha256 text CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    report_event_key text,
    report_sha256 text CHECK (report_sha256 ~ '^[0-9a-f]{64}$'),
    handover_event_key text,
    handover_sha256 text CHECK (handover_sha256 ~ '^[0-9a-f]{64}$'),
    review_until timestamptz,
    restore_manifest_sha256 text CHECK (restore_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (mode <> 'ACTIVE' OR (organization_id IS NOT NULL AND tenant_id IS NOT NULL
        AND source_commit IS NOT NULL AND artifact_sha256 IS NOT NULL
        AND report_event_key IS NOT NULL AND report_sha256 IS NOT NULL
        AND handover_event_key IS NOT NULL AND handover_sha256 IS NOT NULL
        AND review_until IS NOT NULL))
);
INSERT INTO hosting_controlplane.operating_instance
    (instance_id,database_oid,database_system_identifier,generation,mode)
VALUES (md5(random()::text || clock_timestamp()::text),
        (SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()),
        (SELECT system_identifier::text FROM pg_catalog.pg_control_system()),1,'UNCOMMISSIONED');
REVOKE ALL ON hosting_controlplane.operating_instance FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.guard_operating_instance()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Operating instance custody cannot be deleted';
    END IF;
    IF NEW.singleton IS DISTINCT FROM OLD.singleton
       OR NEW.generation <> OLD.generation + 1
       OR NEW.updated_at <= OLD.updated_at
       OR ((NEW.instance_id,NEW.database_oid,NEW.database_system_identifier) IS DISTINCT FROM
           (OLD.instance_id,OLD.database_oid,OLD.database_system_identifier)
           AND NEW.mode <> 'OBSERVATION_ONLY') THEN
        RAISE EXCEPTION 'Operating instance transition requires a new retained generation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER operating_instance_guard BEFORE UPDATE OR DELETE
    ON hosting_controlplane.operating_instance FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.guard_operating_instance();

-- SECURITY DEFINER permits native/grant roles to enforce the gate without
-- giving them DML, locks or cross-tenant custodial evidence access.
CREATE FUNCTION hosting_controlplane.require_operating_instance_active()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE s hosting_controlplane.operating_instance;
BEGIN
    SELECT * INTO s FROM hosting_controlplane.operating_instance WHERE singleton FOR SHARE;
    IF NOT FOUND OR s.mode <> 'ACTIVE' OR s.review_until <= clock_timestamp()
       OR s.database_oid <> (SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database())
       OR s.database_system_identifier <> (SELECT system_identifier::text FROM pg_catalog.pg_control_system()) THEN
        RAISE EXCEPTION 'Operating instance is observation-only, uncommissioned or review-due'
            USING ERRCODE = '42501';
    END IF;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.require_operating_instance_active() FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.lock_operating_instance()
RETURNS SETOF hosting_controlplane.operating_instance
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM hosting_controlplane.operating_instance WHERE singleton
               AND database_system_identifier <>
                   (SELECT system_identifier::text FROM pg_catalog.pg_control_system())) THEN
        RAISE EXCEPTION 'Restored operating cluster identity differs' USING ERRCODE = '42501';
    END IF;
    RETURN QUERY SELECT * FROM hosting_controlplane.operating_instance WHERE singleton FOR SHARE;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.lock_operating_instance() FROM PUBLIC;

CREATE FUNCTION hosting_controlplane.guard_operating_native_claim()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
BEGIN
    IF TG_TABLE_NAME = 'worker_grants' THEN
        IF NEW.operation_kind <> 'DISCOVER_READ' THEN
            PERFORM hosting_controlplane.require_operating_instance_active();
        END IF;
    ELSIF NEW.state = 'IN_FLIGHT' AND NEW.operation_kind <> 'DISCOVER_READ' THEN
        PERFORM hosting_controlplane.require_operating_instance_active();
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_operating_native_claim() FROM PUBLIC;
CREATE TRIGGER operating_grant_interlock BEFORE INSERT
    ON hosting_controlplane.worker_grants FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.guard_operating_native_claim();
CREATE TRIGGER operating_native_interlock BEFORE UPDATE OF state
    ON hosting_controlplane.native_operation_intents FOR EACH ROW
    EXECUTE FUNCTION hosting_controlplane.guard_operating_native_claim();
