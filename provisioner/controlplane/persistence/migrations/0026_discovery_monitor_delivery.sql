-- Unattended monitoring uses the existing independently signed IAM directory.
-- This kind has only DISCOVERY_MONITOR grants; HTTP operator access stays HUMAN.
ALTER TABLE hosting_controlplane.directory_subjects
    DROP CONSTRAINT directory_subjects_identity_kind_check;
ALTER TABLE hosting_controlplane.directory_subjects ADD CONSTRAINT directory_subjects_identity_kind_check
    CHECK (identity_kind IN ('HUMAN', 'WORKER', 'SERVICE'));

CREATE TABLE hosting_controlplane.discovery_alert_deliveries (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    environment_id text NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL,
    alert_id text NOT NULL CHECK (alert_id ~ '^[0-9a-f]{64}$'),
    check_id text NOT NULL,
    check_record_digest text NOT NULL CHECK (check_record_digest ~ '^[0-9a-f]{64}$'),
    owner_id text NOT NULL CHECK (owner_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    sequence bigint NOT NULL CHECK (sequence BETWEEN 1 AND 7),
    event text NOT NULL CHECK (event IN ('DELIVERY_STARTED','DELIVERY_UNKNOWN','DELIVERY_ACCEPTED','ACKNOWLEDGED')),
    attempt_number integer NOT NULL CHECK (attempt_number BETWEEN 1 AND 3),
    intent_json text NOT NULL CHECK (octet_length(intent_json) BETWEEN 1 AND 8192 AND jsonb_typeof(intent_json::jsonb)='object'),
    intent_digest text NOT NULL CHECK (intent_digest ~ '^[0-9a-f]{64}$'),
    receipt_json text CHECK (octet_length(receipt_json) BETWEEN 1 AND 8192 AND jsonb_typeof(receipt_json::jsonb)='object'),
    recorded_by text NOT NULL CHECK (length(recorded_by) BETWEEN 1 AND 512),
    recorded_at timestamptz NOT NULL,
    previous_record_digest text CHECK (previous_record_digest ~ '^[0-9a-f]{64}$'),
    record_digest text NOT NULL CHECK (record_digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (organization_id,tenant_id,environment_id,alert_id,sequence),
    FOREIGN KEY (organization_id,tenant_id,environment_id,check_id)
        REFERENCES hosting_controlplane.discovery_freshness_checks (organization_id,tenant_id,environment_id,check_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,tenant_id,environment_id,site_id,security_domain_id,endpoint_id,native_scope_id,platform_family)
        REFERENCES hosting_controlplane.environment_registrations
        (organization_id,tenant_id,environment_id,site_id,security_domain_id,endpoint_id,native_scope_id,platform_family) ON DELETE RESTRICT,
    CHECK ((sequence=1)=(previous_record_digest IS NULL)),
    CHECK ((event IN ('DELIVERY_ACCEPTED','ACKNOWLEDGED'))=(receipt_json IS NOT NULL)),
    CHECK ((intent_json::jsonb ->> 'alertId') IS NOT DISTINCT FROM alert_id),
    CHECK ((intent_json::jsonb ->> 'checkId') IS NOT DISTINCT FROM check_id),
    CHECK ((intent_json::jsonb ->> 'environmentId') IS NOT DISTINCT FROM environment_id),
    CHECK ((intent_json::jsonb ->> 'checkRecordDigest') IS NOT DISTINCT FROM check_record_digest),
    CHECK ((intent_json::jsonb -> 'collectionRequested') IS NOT DISTINCT FROM 'false'::jsonb),
    CHECK ((intent_json::jsonb -> 'executionAuthorized') IS NOT DISTINCT FROM 'false'::jsonb)
);
CREATE TRIGGER discovery_alert_delivery_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.discovery_alert_deliveries
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

CREATE FUNCTION hosting_controlplane.guard_discovery_alert_delivery() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,hosting_controlplane AS $$
DECLARE previous hosting_controlplane.discovery_alert_deliveries%ROWTYPE;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array(
        'discovery-alert-event',NEW.organization_id,NEW.tenant_id,NEW.environment_id,NEW.alert_id)::text,0));
    SELECT * INTO previous FROM hosting_controlplane.discovery_alert_deliveries
        WHERE organization_id=NEW.organization_id AND tenant_id=NEW.tenant_id
          AND environment_id=NEW.environment_id AND alert_id=NEW.alert_id ORDER BY sequence DESC LIMIT 1;
    IF NOT EXISTS (SELECT 1 FROM hosting_controlplane.discovery_freshness_checks
        WHERE organization_id=NEW.organization_id AND tenant_id=NEW.tenant_id
          AND environment_id=NEW.environment_id AND check_id=NEW.check_id
          AND record_digest=NEW.check_record_digest) THEN
        RAISE EXCEPTION 'Alert intent must retain the exact original freshness check' USING ERRCODE='23514';
    END IF;
    IF NEW.sequence<>COALESCE(previous.sequence,0)+1
        OR NEW.previous_record_digest IS DISTINCT FROM previous.record_digest
        OR NEW.recorded_at<previous.recorded_at THEN
        RAISE EXCEPTION 'Alert delivery requires its exact retained predecessor' USING ERRCODE='23514';
    END IF;
    IF previous.sequence IS NULL THEN
        IF NEW.event<>'DELIVERY_STARTED' OR NEW.attempt_number<>1 THEN
            RAISE EXCEPTION 'Alert delivery must start before any effect' USING ERRCODE='23514';
        END IF;
    ELSE
        IF (NEW.owner_id,NEW.intent_digest,NEW.check_id,NEW.check_record_digest,NEW.recorded_by)
            IS DISTINCT FROM (previous.owner_id,previous.intent_digest,previous.check_id,previous.check_record_digest,previous.recorded_by)
            OR NOT (
                (NEW.event='DELIVERY_STARTED' AND previous.event IN ('DELIVERY_STARTED','DELIVERY_UNKNOWN')
                    AND NEW.attempt_number=previous.attempt_number+1)
                OR (NEW.event IN ('DELIVERY_UNKNOWN','DELIVERY_ACCEPTED','ACKNOWLEDGED') AND previous.event='DELIVERY_STARTED'
                    AND NEW.attempt_number=previous.attempt_number)
                OR (NEW.event='ACKNOWLEDGED' AND previous.event='DELIVERY_ACCEPTED'
                    AND NEW.attempt_number=previous.attempt_number)) THEN
            RAISE EXCEPTION 'Alert delivery transition or identity changed' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.guard_discovery_alert_delivery() FROM PUBLIC;
CREATE TRIGGER discovery_alert_delivery_sequence BEFORE INSERT ON hosting_controlplane.discovery_alert_deliveries
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_discovery_alert_delivery();
REVOKE ALL ON hosting_controlplane.discovery_alert_deliveries FROM PUBLIC;
ALTER TABLE hosting_controlplane.discovery_alert_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_alert_deliveries FORCE ROW LEVEL SECURITY;
CREATE POLICY discovery_alert_delivery_tenant ON hosting_controlplane.discovery_alert_deliveries
    USING (organization_id=current_setting('app.organization_id',true) AND tenant_id=current_setting('app.tenant_id',true))
    WITH CHECK (organization_id=current_setting('app.organization_id',true) AND tenant_id=current_setting('app.tenant_id',true));
CREATE POLICY discovery_alert_delivery_no_worker ON hosting_controlplane.discovery_alert_deliveries
    AS RESTRICTIVE FOR ALL USING (NOT hosting_controlplane.is_site_worker_role())
    WITH CHECK (NOT hosting_controlplane.is_site_worker_role());
