-- Chain every audit_events row in tenant commit order. This migration briefly
-- takes an ACCESS EXCLUSIVE lock to backfill the legacy append-only rows by
-- event_id. Future inserts acquire a tenant stream row lock, so a later event
-- cannot commit before its predecessor. No application role needs permission
-- to update audit rows or audit_streams.
LOCK TABLE hosting_controlplane.audit_events IN ACCESS EXCLUSIVE MODE;

CREATE TABLE hosting_controlplane.audit_streams (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    last_sequence bigint NOT NULL DEFAULT 0 CHECK (last_sequence >= 0),
    head_hash text NOT NULL DEFAULT repeat('0', 64)
        CHECK (head_hash ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (organization_id, tenant_id)
);

ALTER TABLE hosting_controlplane.audit_events
    ADD COLUMN audit_sequence bigint,
    ADD COLUMN previous_hash text,
    ADD COLUMN event_hash text;

-- Length-prefixed UTF-8 fields avoid delimiter ambiguity. The verifier
-- independently recomputes these bytes from the selected row values.
CREATE FUNCTION hosting_controlplane.audit_hash_parts(parts text[])
RETURNS text LANGUAGE sql IMMUTABLE STRICT SET search_path = pg_catalog AS $$
    SELECT encode(sha256(convert_to(
        (SELECT string_agg(octet_length(convert_to(part, 'UTF8'))::text || ':' || part,
                           '' ORDER BY ordinal)
         FROM unnest(parts) WITH ORDINALITY AS fields(part, ordinal)), 'UTF8')), 'hex');
$$;

CREATE FUNCTION hosting_controlplane.audit_event_hash(
    event_id bigint, organization_id text, tenant_id text,
    actor_id text, correlation_id text, action text, record_kind text,
    record_id text, revision bigint, record_digest text, details jsonb,
    occurred_at timestamptz, audit_sequence bigint, previous_hash text)
RETURNS text LANGUAGE sql STABLE STRICT SET search_path = pg_catalog AS $$
    SELECT hosting_controlplane.audit_hash_parts(ARRAY[
        'audit-v1', event_id::text, organization_id, tenant_id,
        actor_id, correlation_id, action, record_kind, record_id,
        revision::text, record_digest, details::text,
        to_char(occurred_at AT TIME ZONE 'UTC',
                'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
        audit_sequence::text, previous_hash]);
$$;

-- The migration owner cannot read FORCE RLS rows without a scope. Relaxing
-- FORCE and the append-only trigger here is confined to this locked migration
-- transaction, then reinstated before commit.
ALTER TABLE hosting_controlplane.audit_events NO FORCE ROW LEVEL SECURITY;
DROP TRIGGER audit_append_only ON hosting_controlplane.audit_events;
DO $$
DECLARE
    item record;
    prior_sequence bigint;
    prior_hash text;
    next_hash text;
BEGIN
    FOR item IN SELECT * FROM hosting_controlplane.audit_events
                ORDER BY organization_id, tenant_id, event_id LOOP
        INSERT INTO hosting_controlplane.audit_streams (organization_id, tenant_id)
            VALUES (item.organization_id, item.tenant_id) ON CONFLICT DO NOTHING;
        SELECT last_sequence, head_hash INTO prior_sequence, prior_hash
          FROM hosting_controlplane.audit_streams
         WHERE organization_id = item.organization_id AND tenant_id = item.tenant_id
         FOR UPDATE;
        next_hash := hosting_controlplane.audit_event_hash(
            item.event_id, item.organization_id, item.tenant_id,
            item.actor_id, item.correlation_id, item.action, item.record_kind,
            item.record_id, item.revision, item.record_digest, item.details,
            item.occurred_at, prior_sequence + 1, prior_hash);
        UPDATE hosting_controlplane.audit_events
           SET audit_sequence = prior_sequence + 1, previous_hash = prior_hash,
               event_hash = next_hash WHERE event_id = item.event_id;
        UPDATE hosting_controlplane.audit_streams
           SET last_sequence = prior_sequence + 1, head_hash = next_hash
         WHERE organization_id = item.organization_id AND tenant_id = item.tenant_id;
    END LOOP;
END;
$$;

ALTER TABLE hosting_controlplane.audit_events
    ALTER COLUMN audit_sequence SET NOT NULL,
    ALTER COLUMN previous_hash SET NOT NULL,
    ALTER COLUMN event_hash SET NOT NULL,
    ADD CONSTRAINT audit_sequence_positive CHECK (audit_sequence > 0),
    ADD CONSTRAINT audit_previous_hash_format CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
    ADD CONSTRAINT audit_event_hash_format CHECK (event_hash ~ '^[0-9a-f]{64}$'),
    ADD CONSTRAINT audit_tenant_sequence UNIQUE (organization_id, tenant_id, audit_sequence);

CREATE FUNCTION hosting_controlplane.chain_audit_insert()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE
    prior_sequence bigint;
    prior_hash text;
BEGIN
    IF NEW.organization_id IS DISTINCT FROM current_setting('app.organization_id', true)
       OR NEW.tenant_id IS DISTINCT FROM current_setting('app.tenant_id', true) THEN
        RAISE EXCEPTION 'Audit tenant context is missing or mismatched';
    END IF;
    INSERT INTO hosting_controlplane.audit_streams (organization_id, tenant_id)
        VALUES (NEW.organization_id, NEW.tenant_id) ON CONFLICT DO NOTHING;
    SELECT last_sequence, head_hash INTO prior_sequence, prior_hash
      FROM hosting_controlplane.audit_streams
     WHERE organization_id = NEW.organization_id AND tenant_id = NEW.tenant_id
     FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Audit stream is unavailable in tenant context';
    END IF;
    NEW.audit_sequence := prior_sequence + 1;
    NEW.previous_hash := prior_hash;
    NEW.event_hash := hosting_controlplane.audit_event_hash(
        NEW.event_id, NEW.organization_id, NEW.tenant_id, NEW.actor_id,
        NEW.correlation_id, NEW.action, NEW.record_kind, NEW.record_id,
        NEW.revision, NEW.record_digest, NEW.details, NEW.occurred_at,
        NEW.audit_sequence, NEW.previous_hash);
    UPDATE hosting_controlplane.audit_streams
       SET last_sequence = NEW.audit_sequence, head_hash = NEW.event_hash
     WHERE organization_id = NEW.organization_id AND tenant_id = NEW.tenant_id;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION hosting_controlplane.chain_audit_insert() FROM PUBLIC;
CREATE TRIGGER audit_chain_insert BEFORE INSERT
    ON hosting_controlplane.audit_events
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.chain_audit_insert();
CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE
    ON hosting_controlplane.audit_events
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
ALTER TABLE hosting_controlplane.audit_events FORCE ROW LEVEL SECURITY;

ALTER TABLE hosting_controlplane.audit_streams ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.audit_streams FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_audit_streams ON hosting_controlplane.audit_streams
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
REVOKE ALL ON hosting_controlplane.audit_streams FROM PUBLIC;
