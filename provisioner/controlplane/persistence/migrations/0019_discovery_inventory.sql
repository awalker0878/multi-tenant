-- Brownfield discovery is a read-only observation plane. A declared environment
-- supplies an exact selector, not proof of ownership or permission to mutate.
-- Grant table access only to separate discovery ingest/read roles after review;
-- site worker and ordinary HTTP roles receive no DML on these tables.
ALTER TABLE hosting_controlplane.environment_registrations
    ADD CONSTRAINT environment_discovery_selector UNIQUE
    (organization_id, tenant_id, environment_id, site_id,
     security_domain_id, endpoint_id, native_scope_id, platform_family);

CREATE TABLE hosting_controlplane.discovery_campaigns (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    campaign_id text NOT NULL CHECK
        (campaign_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    environment_id text NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL,
    authority_reference text NOT NULL CHECK
        (authority_reference ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    collector_id text NOT NULL CHECK
        (collector_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    allowed_kinds text[] NOT NULL CHECK
        (cardinality(allowed_kinds) BETWEEN 1 AND 12 AND
         allowed_kinds <@ ARRAY['vm','disk','nic','volume','image','network',
                                'pool','cluster','host','datastore','quota',
                                'dataset']::text[]),
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK
        (expires_at > issued_at AND expires_at <= issued_at + interval '1 hour'),
    max_pages integer NOT NULL CHECK (max_pages BETWEEN 1 AND 1000),
    max_objects integer NOT NULL CHECK (max_objects BETWEEN 1 AND 100000),
    max_page_size integer NOT NULL CHECK (max_page_size BETWEEN 1 AND 500),
    authorization_digest text NOT NULL CHECK
        (authorization_digest ~ '^[0-9a-f]{64}$'),
    verified_by text NOT NULL CHECK (length(verified_by) BETWEEN 1 AND 512),
    verification_reference text NOT NULL CHECK (length(verification_reference) BETWEEN 1 AND 512),
    registered_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, campaign_id),
    UNIQUE (organization_id, tenant_id, campaign_id, environment_id, site_id,
            security_domain_id, endpoint_id, native_scope_id, platform_family),
    FOREIGN KEY (organization_id, tenant_id, environment_id, site_id,
                 security_domain_id, endpoint_id, native_scope_id, platform_family)
        REFERENCES hosting_controlplane.environment_registrations
        (organization_id, tenant_id, environment_id, site_id,
         security_domain_id, endpoint_id, native_scope_id, platform_family)
        ON DELETE RESTRICT
);
CREATE INDEX discovery_campaign_scope_page
    ON hosting_controlplane.discovery_campaigns
    (organization_id, tenant_id, environment_id, campaign_id);

CREATE TABLE hosting_controlplane.discovery_generations (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    environment_id text NOT NULL,
    generation bigint NOT NULL CHECK (generation > 0),
    campaign_id text NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL,
    authorization_digest text NOT NULL CHECK
        (authorization_digest ~ '^[0-9a-f]{64}$'),
    result_digest text NOT NULL CHECK (result_digest ~ '^[0-9a-f]{64}$'),
    captured_at timestamptz NOT NULL,
    completeness text NOT NULL CHECK (completeness IN ('COMPLETE','PARTIAL','UNKNOWN')),
    collection_errors text[] NOT NULL DEFAULT '{}'::text[],
    missing_privileges text[] NOT NULL DEFAULT '{}'::text[],
    object_count integer NOT NULL CHECK (object_count BETWEEN 0 AND 100000),
    published_by text NOT NULL CHECK (length(published_by) BETWEEN 1 AND 512),
    verification_reference text NOT NULL CHECK (length(verification_reference) BETWEEN 1 AND 512),
    published_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (organization_id, tenant_id, environment_id, generation),
    UNIQUE (organization_id, tenant_id, campaign_id),
    UNIQUE (organization_id, tenant_id, environment_id, generation,
            endpoint_id, native_scope_id, platform_family),
    FOREIGN KEY (organization_id, tenant_id, campaign_id, environment_id, site_id,
                 security_domain_id, endpoint_id, native_scope_id, platform_family)
        REFERENCES hosting_controlplane.discovery_campaigns
        (organization_id, tenant_id, campaign_id, environment_id, site_id,
         security_domain_id, endpoint_id, native_scope_id, platform_family)
        ON DELETE RESTRICT,
    CHECK (completeness <> 'COMPLETE' OR
           (cardinality(collection_errors) = 0 AND cardinality(missing_privileges) = 0))
);
CREATE INDEX discovery_generations_scope_page
    ON hosting_controlplane.discovery_generations
    (organization_id, tenant_id, site_id, security_domain_id, environment_id, generation);

-- Stable native IDs are keys. Human names are just immutable observed facts in
-- each generation, so a rename cannot rewrite history or create a new owner.
CREATE TABLE hosting_controlplane.discovery_observations (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    environment_id text NOT NULL,
    generation bigint NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL,
    resource_kind text NOT NULL CHECK
        (resource_kind IN ('vm','disk','nic','volume','image','network',
                           'pool','cluster','host','datastore','quota','dataset')),
    native_id text NOT NULL CHECK
        (length(native_id) BETWEEN 1 AND 512 AND btrim(native_id) <> ''
         AND native_id !~ '[[:cntrl:]]'),
    -- Preserve canonical JSON bytes for the exact signed object digest; jsonb
    -- normalization can change number spellings during readback.
    facts_json text NOT NULL CHECK
        (octet_length(facts_json) <= 600000
         AND jsonb_typeof(facts_json::jsonb) = 'array'
         AND jsonb_array_length(facts_json::jsonb) BETWEEN 1 AND 64),
    object_digest text NOT NULL CHECK (object_digest ~ '^[0-9a-f]{64}$'),
    PRIMARY KEY (organization_id, tenant_id, environment_id, generation,
                 resource_kind, native_id),
    FOREIGN KEY (organization_id, tenant_id, environment_id, generation,
                 endpoint_id, native_scope_id, platform_family)
        REFERENCES hosting_controlplane.discovery_generations
        (organization_id, tenant_id, environment_id, generation,
         endpoint_id, native_scope_id, platform_family)
        ON DELETE RESTRICT
);
CREATE INDEX discovery_observation_identity_history
    ON hosting_controlplane.discovery_observations
    (organization_id, tenant_id, environment_id, resource_kind, native_id, generation);

-- An absence candidate is only a comparison between two complete, comparable
-- enumerations. It is never a deletion, owner release, or execution grant.
CREATE TABLE hosting_controlplane.discovery_absence_candidates (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    environment_id text NOT NULL,
    generation bigint NOT NULL,
    resource_kind text NOT NULL,
    native_id text NOT NULL,
    prior_generation bigint NOT NULL CHECK (prior_generation > 0),
    PRIMARY KEY (organization_id, tenant_id, environment_id, generation,
                 resource_kind, native_id),
    FOREIGN KEY (organization_id, tenant_id, environment_id, generation)
        REFERENCES hosting_controlplane.discovery_generations
        (organization_id, tenant_id, environment_id, generation) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tenant_id, environment_id, prior_generation,
                 resource_kind, native_id)
        REFERENCES hosting_controlplane.discovery_observations
        (organization_id, tenant_id, environment_id, generation,
         resource_kind, native_id) ON DELETE RESTRICT,
    CHECK (prior_generation < generation)
);

CREATE FUNCTION hosting_controlplane.guard_discovery_absence()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE previous_complete bigint;
BEGIN
    SELECT max(g.generation) INTO previous_complete
    FROM hosting_controlplane.discovery_generations g
    JOIN hosting_controlplane.discovery_campaigns c
      ON (c.organization_id, c.tenant_id, c.campaign_id) =
         (g.organization_id, g.tenant_id, g.campaign_id)
    WHERE g.organization_id = NEW.organization_id
      AND g.tenant_id = NEW.tenant_id
      AND g.environment_id = NEW.environment_id
      AND g.generation < NEW.generation AND g.completeness = 'COMPLETE'
      AND NEW.resource_kind = ANY(c.allowed_kinds);
    IF previous_complete IS DISTINCT FROM NEW.prior_generation OR
       NOT EXISTS (
           SELECT 1 FROM hosting_controlplane.discovery_generations g
           JOIN hosting_controlplane.discovery_campaigns c
             ON (c.organization_id, c.tenant_id, c.campaign_id) =
                (g.organization_id, g.tenant_id, g.campaign_id)
           WHERE g.organization_id = NEW.organization_id
             AND g.tenant_id = NEW.tenant_id
             AND g.environment_id = NEW.environment_id
             AND g.generation = NEW.generation AND g.completeness = 'COMPLETE'
             AND NEW.resource_kind = ANY(c.allowed_kinds)) OR
       EXISTS (
           SELECT 1 FROM hosting_controlplane.discovery_observations o
           WHERE (o.organization_id, o.tenant_id, o.environment_id,
                  o.generation, o.resource_kind, o.native_id) =
                 (NEW.organization_id, NEW.tenant_id, NEW.environment_id,
                  NEW.generation, NEW.resource_kind, NEW.native_id)) THEN
        RAISE EXCEPTION 'Absence requires comparable complete generations';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER discovery_absence_guard BEFORE INSERT
    ON hosting_controlplane.discovery_absence_candidates
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_discovery_absence();
REVOKE ALL ON FUNCTION hosting_controlplane.guard_discovery_absence() FROM PUBLIC;

CREATE TRIGGER discovery_campaign_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.discovery_campaigns
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER discovery_generation_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.discovery_generations
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER discovery_observation_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.discovery_observations
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();
CREATE TRIGGER discovery_absence_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.discovery_absence_candidates
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

REVOKE ALL ON hosting_controlplane.discovery_campaigns,
    hosting_controlplane.discovery_generations,
    hosting_controlplane.discovery_observations,
    hosting_controlplane.discovery_absence_candidates FROM PUBLIC;
ALTER TABLE hosting_controlplane.discovery_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_campaigns FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_generations FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_observations FORCE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_absence_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.discovery_absence_candidates FORCE ROW LEVEL SECURITY;
CREATE POLICY discovery_campaign_tenant ON hosting_controlplane.discovery_campaigns
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY discovery_generation_tenant ON hosting_controlplane.discovery_generations
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY discovery_observation_tenant ON hosting_controlplane.discovery_observations
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY discovery_absence_tenant ON hosting_controlplane.discovery_absence_candidates
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
