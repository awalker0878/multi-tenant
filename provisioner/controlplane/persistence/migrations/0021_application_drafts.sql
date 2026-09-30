-- Unreviewed human enrichment is separate from discovery, accepted applications,
-- ownership and execution authority. No role or native permission is issued here.
ALTER TABLE hosting_controlplane.discovery_generations
    ADD CONSTRAINT discovery_generation_result_binding UNIQUE
    (organization_id, tenant_id, environment_id, generation, result_digest);

CREATE TABLE hosting_controlplane.application_draft_revisions (
    organization_id text NOT NULL,
    tenant_id text NOT NULL,
    environment_id text NOT NULL,
    site_id text NOT NULL,
    security_domain_id text NOT NULL,
    endpoint_id text NOT NULL,
    native_scope_id text NOT NULL,
    platform_family text NOT NULL,
    application_group_id text NOT NULL CHECK
        (application_group_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    revision bigint NOT NULL CHECK (revision > 0),
    generation bigint NOT NULL CHECK (generation > 0),
    result_digest text NOT NULL CHECK (result_digest ~ '^[0-9a-f]{64}$'),
    proposal_json text NOT NULL CHECK
        (octet_length(proposal_json) BETWEEN 1 AND 131072
         AND jsonb_typeof(proposal_json::jsonb) = 'object'),
    proposal_digest text NOT NULL CHECK (proposal_digest ~ '^[0-9a-f]{64}$'),
    recorded_by text NOT NULL CHECK (length(recorded_by) BETWEEN 1 AND 512),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    record_digest text NOT NULL CHECK (record_digest ~ '^[0-9a-f]{64}$'),
    status text NOT NULL DEFAULT 'UNREVIEWED' CHECK (status = 'UNREVIEWED'),
    PRIMARY KEY (organization_id, tenant_id, environment_id, application_group_id, revision),
    FOREIGN KEY (organization_id, tenant_id, environment_id, site_id,
                 security_domain_id, endpoint_id, native_scope_id, platform_family)
        REFERENCES hosting_controlplane.environment_registrations
        (organization_id, tenant_id, environment_id, site_id,
         security_domain_id, endpoint_id, native_scope_id, platform_family) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tenant_id, environment_id, generation, result_digest)
        REFERENCES hosting_controlplane.discovery_generations
        (organization_id, tenant_id, environment_id, generation, result_digest) ON DELETE RESTRICT,
    CHECK ((proposal_json::jsonb ->> 'format') IS NOT DISTINCT FROM
           'hosting-application-group-candidate/1'),
    CHECK ((proposal_json::jsonb ->> 'discoveryDigest') IS NOT DISTINCT FROM result_digest),
    CHECK ((proposal_json::jsonb -> 'draft' ->> 'applicationGroupId') IS NOT DISTINCT FROM application_group_id)
);
CREATE TRIGGER application_draft_immutable BEFORE UPDATE OR DELETE
    ON hosting_controlplane.application_draft_revisions
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.prevent_append_only_changes();

CREATE FUNCTION hosting_controlplane.guard_application_draft_revision() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, hosting_controlplane AS $$
DECLARE expected bigint;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array(
        'application-draft', NEW.organization_id, NEW.tenant_id,
        NEW.environment_id, NEW.application_group_id)::text, 0));
    SELECT COALESCE(MAX(revision), 0) + 1 INTO expected
      FROM hosting_controlplane.application_draft_revisions
      WHERE organization_id=NEW.organization_id AND tenant_id=NEW.tenant_id
        AND environment_id=NEW.environment_id AND application_group_id=NEW.application_group_id;
    IF NEW.revision <> expected THEN
        RAISE EXCEPTION 'Application draft revisions must be consecutive' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER application_draft_revision BEFORE INSERT
    ON hosting_controlplane.application_draft_revisions
    FOR EACH ROW EXECUTE FUNCTION hosting_controlplane.guard_application_draft_revision();
REVOKE ALL ON FUNCTION hosting_controlplane.guard_application_draft_revision() FROM PUBLIC;
REVOKE ALL ON hosting_controlplane.application_draft_revisions FROM PUBLIC;
ALTER TABLE hosting_controlplane.application_draft_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hosting_controlplane.application_draft_revisions FORCE ROW LEVEL SECURITY;
CREATE POLICY application_draft_tenant ON hosting_controlplane.application_draft_revisions
    USING (organization_id = current_setting('app.organization_id', true)
       AND tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (organization_id = current_setting('app.organization_id', true)
            AND tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY application_draft_no_site_worker ON hosting_controlplane.application_draft_revisions
    AS RESTRICTIVE FOR ALL
    USING (NOT hosting_controlplane.is_site_worker_role())
    WITH CHECK (NOT hosting_controlplane.is_site_worker_role());
